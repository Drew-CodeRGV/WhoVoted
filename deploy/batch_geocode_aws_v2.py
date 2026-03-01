#!/usr/bin/env python3
"""Batch geocode all ungeocoded Hidalgo County voter addresses using AWS Location Service."""
import os, sys, time, json, sqlite3, logging, argparse, threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted')
from dotenv import load_dotenv
load_dotenv('/opt/whovoted/.env')
import boto3
from botocore.config import Config as BotoConfig
from botocore.exceptions import ClientError

DB_PATH = '/opt/whovoted/data/whovoted.db'
STATUS_FILE = '/opt/whovoted/data/batch_geocode_status.json'
PLACE_INDEX = os.environ.get('AWS_LOCATION_PLACE_INDEX', 'WhoVotedPlaceIndex')
REGION = os.environ.get('AWS_REGION', os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
COUNTY = 'Hidalgo'
os.makedirs('/opt/whovoted/logs', exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s',
    handlers=[logging.FileHandler('/opt/whovoted/logs/batch_geocode.log'), logging.StreamHandler()])
log = logging.getLogger('batch_geocode')

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn

def ensure_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS voter_addresses (
            vuid TEXT NOT NULL, address_key TEXT NOT NULL, address_raw TEXT,
            created_at TEXT DEFAULT (datetime('now')), PRIMARY KEY (vuid));
        CREATE INDEX IF NOT EXISTS idx_va_address_key ON voter_addresses(address_key);""")
    conn.commit()

def normalize_address(addr):
    return addr.strip().upper()

def write_status(status):
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception:
        pass


class AWSBatchGeocoder:
    def __init__(self, max_workers=20):
        self.max_workers = max_workers
        cfg = BotoConfig(max_pool_connections=max_workers + 5, retries={'max_attempts': 3, 'mode': 'adaptive'})
        self.client = boto3.client('location', region_name=REGION, config=cfg)
        self.place_index = PLACE_INDEX
        self.stats = {'api_calls': 0, 'successes': 0, 'failures': 0, 'throttles': 0}
        self._lock = threading.Lock()

    def geocode_one(self, address):
        try:
            with self._lock:
                self.stats['api_calls'] += 1
            resp = self.client.search_place_index_for_text(IndexName=self.place_index, Text=address, MaxResults=1, FilterCountries=['USA'])
            if resp.get('Results'):
                place = resp['Results'][0]['Place']
                coords = place['Geometry']['Point']
                with self._lock:
                    self.stats['successes'] += 1
                return normalize_address(address), {'lat': float(coords[1]), 'lng': float(coords[0]), 'display_name': place.get('Label', address), 'source': 'aws_batch', 'relevance': resp['Results'][0].get('Relevance', 0)}
            else:
                with self._lock:
                    self.stats['failures'] += 1
                return normalize_address(address), None
        except ClientError as e:
            code = e.response['Error']['Code']
            with self._lock:
                if code == 'ThrottlingException': self.stats['throttles'] += 1
                else: self.stats['failures'] += 1
            if code == 'ThrottlingException':
                time.sleep(2)
                try:
                    resp = self.client.search_place_index_for_text(IndexName=self.place_index, Text=address, MaxResults=1, FilterCountries=['USA'])
                    if resp.get('Results'):
                        place = resp['Results'][0]['Place']
                        coords = place['Geometry']['Point']
                        with self._lock: self.stats['successes'] += 1
                        return normalize_address(address), {'lat': float(coords[1]), 'lng': float(coords[0]), 'display_name': place.get('Label', address), 'source': 'aws_batch_retry', 'relevance': resp['Results'][0].get('Relevance', 0)}
                except Exception: pass
            return normalize_address(address), None
        except Exception:
            with self._lock: self.stats['failures'] += 1
            return normalize_address(address), None


def run(max_workers=20, batch_size=500, dry_run=False):
    log.info("=" * 60)
    log.info("BATCH GEOCODE START")
    log.info("Workers: %d, Batch size: %d, Dry run: %s", max_workers, batch_size, dry_run)
    log.info("=" * 60)
    conn = get_conn()
    ensure_tables(conn)
    status = {'started_at': datetime.now().isoformat(), 'phase': 'init', 'total_voters': 0,
              'already_geocoded': 0, 'unique_addresses': 0, 'cache_resolved': 0,
              'voter_resolved': 0, 'need_aws': 0, 'aws_done': 0, 'aws_success': 0,
              'aws_fail': 0, 'backfilled': 0, 'completed': False}
    write_status(status)

    # Phase 1: Gather ungeocoded voters
    log.info("Phase 1: Gathering ungeocoded voters...")
    status['phase'] = 'gather'
    write_status(status)
    rows = conn.execute("SELECT vuid, address, city, zip FROM voters WHERE county = ? AND (geocoded = 0 OR geocoded IS NULL) AND address IS NOT NULL AND address != ''", (COUNTY,)).fetchall()
    total_need = len(rows)
    already = conn.execute("SELECT COUNT(*) FROM voters WHERE county = ? AND geocoded = 1", (COUNTY,)).fetchone()[0]
    status['total_voters'] = total_need + already
    status['already_geocoded'] = already
    log.info("Total voters: %d, Already geocoded: %d, Need geocoding: %d", total_need + already, already, total_need)
    if total_need == 0:
        log.info("All voters already geocoded!")
        status['completed'] = True
        write_status(status)
        conn.close()
        return

    addr_to_vuids = {}
    for r in rows:
        raw = "%s, %s, TX %s" % (r['address'], r['city'] or '', r['zip'] or '')
        key = normalize_address(raw)
        if key not in addr_to_vuids:
            addr_to_vuids[key] = {'raw': raw, 'vuids': []}
        addr_to_vuids[key]['vuids'].append(r['vuid'])
    unique_count = len(addr_to_vuids)
    status['unique_addresses'] = unique_count
    log.info("Unique addresses: %d", unique_count)

    # Phase 2: Check geocoding_cache
    log.info("Phase 2: Checking geocoding_cache...")
    status['phase'] = 'cache_check'
    write_status(status)
    all_keys = list(addr_to_vuids.keys())
    cache_resolved = {}
    for i in range(0, len(all_keys), 500):
        chunk = all_keys[i:i+500]
        ph = ','.join('?' * len(chunk))
        cached = conn.execute("SELECT address_key, lat, lng, display_name FROM geocoding_cache WHERE address_key IN (%s)" % ph, chunk).fetchall()
        for c in cached:
            if c['lat'] and c['lng']:
                cache_resolved[c['address_key']] = {'lat': c['lat'], 'lng': c['lng'], 'display_name': c['display_name']}
    status['cache_resolved'] = len(cache_resolved)
    log.info("Cache hits: %d", len(cache_resolved))

    # Phase 3: Check already-geocoded voters at same address
    log.info("Phase 3: Checking geocoded voters for address matches...")
    status['phase'] = 'voter_match'
    write_status(status)
    voter_resolved = {}
    remaining_keys = [k for k in all_keys if k not in cache_resolved]
    # Bulk load all geocoded addresses from voters table (one query instead of 188K)
    log.info("Loading all geocoded voter addresses for bulk matching...")
    geo_rows = conn.execute("SELECT DISTINCT UPPER(TRIM(address)) as addr_upper, lat, lng FROM voters WHERE county = ? AND geocoded = 1 AND lat IS NOT NULL AND lng IS NOT NULL", (COUNTY,)).fetchall()
    geo_addr_map = {r['addr_upper']: (r['lat'], r['lng']) for r in geo_rows}
    log.info("Loaded %d unique geocoded addresses for matching", len(geo_addr_map))
    for key in remaining_keys:
        info = addr_to_vuids[key]
        # Try matching the raw address part (before city/state)
        raw_addr = info['raw'].split(',')[0].strip().upper() if ',' in info['raw'] else info['raw'].strip().upper()
        if raw_addr in geo_addr_map:
            lat, lng = geo_addr_map[raw_addr]
            voter_resolved[key] = {'lat': lat, 'lng': lng, 'display_name': ''}
    status['voter_resolved'] = len(voter_resolved)
    log.info("Voter-match hits: %d", len(voter_resolved))

    all_resolved = {}
    all_resolved.update(cache_resolved)
    all_resolved.update(voter_resolved)
    if voter_resolved:
        now = datetime.now().isoformat()
        for key, val in voter_resolved.items():
            conn.execute("INSERT INTO geocoding_cache (address_key, lat, lng, display_name, source, cached_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(address_key) DO NOTHING",
                         (key, val['lat'], val['lng'], val.get('display_name', ''), 'voter_match', now))
        conn.commit()

    log.info("Applying resolved coords to voters...")
    applied = 0
    now = datetime.now().isoformat()
    for key, coords in all_resolved.items():
        vuids = addr_to_vuids[key]['vuids']
        for i in range(0, len(vuids), 500):
            chunk = vuids[i:i+500]
            ph = ','.join('?' * len(chunk))
            conn.execute("UPDATE voters SET lat = ?, lng = ?, geocoded = 1, updated_at = ? WHERE vuid IN (%s) AND (geocoded = 0 OR geocoded IS NULL)" % ph,
                         [coords['lat'], coords['lng'], now] + chunk)
            applied += len(chunk)
        for v in vuids:
            conn.execute("INSERT INTO voter_addresses (vuid, address_key, address_raw) VALUES (?, ?, ?) ON CONFLICT(vuid) DO UPDATE SET address_key = excluded.address_key",
                         (v, key, addr_to_vuids[key]['raw']))
    conn.commit()
    log.info("Applied resolved coords to %d voters", applied)

    # Phase 4: AWS geocoding for remaining
    need_aws = [k for k in all_keys if k not in all_resolved]
    status['need_aws'] = len(need_aws)
    log.info("Need AWS geocoding: %d", len(need_aws))
    write_status(status)
    if dry_run:
        log.info("DRY RUN - skipping AWS geocoding")
        status['completed'] = True
        write_status(status)
        conn.close()
        return
    if not need_aws:
        log.info("No addresses need AWS geocoding!")
        status['phase'] = 'done'
        status['completed'] = True
        write_status(status)
        conn.close()
        return

    log.info("Phase 4: AWS geocoding %d addresses with %d workers...", len(need_aws), max_workers)
    status['phase'] = 'aws_geocode'
    write_status(status)
    geocoder = AWSBatchGeocoder(max_workers=max_workers)
    aws_results = {}
    done_count = 0
    for batch_start in range(0, len(need_aws), batch_size):
        batch_keys = need_aws[batch_start:batch_start + batch_size]
        batch_addrs = [(addr_to_vuids[k]['raw'], k) for k in batch_keys]
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(geocoder.geocode_one, raw): key for raw, key in batch_addrs}
            for future in as_completed(futures):
                try:
                    addr_key, result = future.result()
                    if result:
                        aws_results[addr_key] = result
                except Exception as e:
                    log.warning("Future error: %s", e)
                done_count += 1
        new_cache = []
        now2 = datetime.now().isoformat()
        for key in batch_keys:
            if key in aws_results:
                r = aws_results[key]
                new_cache.append({'address_key': key, 'lat': r['lat'], 'lng': r['lng'], 'display_name': r.get('display_name', ''), 'source': r.get('source', 'aws_batch')})
                vuids = addr_to_vuids[key]['vuids']
                for i in range(0, len(vuids), 500):
                    chunk = vuids[i:i+500]
                    ph = ','.join('?' * len(chunk))
                    conn.execute("UPDATE voters SET lat = ?, lng = ?, geocoded = 1, updated_at = ? WHERE vuid IN (%s)" % ph, [r['lat'], r['lng'], now2] + chunk)
                for v in vuids:
                    conn.execute("INSERT INTO voter_addresses (vuid, address_key, address_raw) VALUES (?, ?, ?) ON CONFLICT(vuid) DO UPDATE SET address_key = excluded.address_key", (v, key, addr_to_vuids[key]['raw']))
        for e in new_cache:
            conn.execute("INSERT INTO geocoding_cache (address_key, lat, lng, display_name, source, cached_at) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT(address_key) DO UPDATE SET lat = excluded.lat, lng = excluded.lng, display_name = excluded.display_name, source = excluded.source, cached_at = excluded.cached_at",
                         (e['address_key'], e['lat'], e['lng'], e['display_name'], e['source'], now2))
        conn.commit()
        status['aws_done'] = done_count
        status['aws_success'] = geocoder.stats['successes']
        status['aws_fail'] = geocoder.stats['failures']
        write_status(status)
        log.info("AWS progress: %d/%d | Success: %d | Fail: %d | Throttles: %d", done_count, len(need_aws), geocoder.stats['successes'], geocoder.stats['failures'], geocoder.stats['throttles'])

    # Phase 5: Final stats
    log.info("Phase 5: Final stats...")
    status['phase'] = 'done'
    final_geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE county = ? AND geocoded = 1", (COUNTY,)).fetchone()[0]
    final_total = conn.execute("SELECT COUNT(*) FROM voters WHERE county = ?", (COUNTY,)).fetchone()[0]
    cache_size = conn.execute("SELECT COUNT(*) FROM geocoding_cache").fetchone()[0]
    status['final_geocoded'] = final_geocoded
    status['final_total'] = final_total
    status['cache_size'] = cache_size
    status['completed'] = True
    status['completed_at'] = datetime.now().isoformat()
    status['backfilled'] = applied + geocoder.stats['successes']
    write_status(status)
    log.info("=" * 60)
    log.info("BATCH GEOCODE COMPLETE")
    log.info("Total voters: %d", final_total)
    log.info("Geocoded: %d (%.1f%%)", final_geocoded, final_geocoded/final_total*100)
    log.info("Cache size: %d", cache_size)
    log.info("AWS calls: %d", geocoder.stats['api_calls'])
    log.info("AWS successes: %d", geocoder.stats['successes'])
    log.info("AWS failures: %d", geocoder.stats['failures'])
    log.info("AWS throttles: %d", geocoder.stats['throttles'])
    log.info("=" * 60)
    conn.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Batch geocode voter addresses')
    parser.add_argument('--workers', type=int, default=20)
    parser.add_argument('--batch-size', type=int, default=500)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    run(max_workers=args.workers, batch_size=args.batch_size, dry_run=args.dry_run)
