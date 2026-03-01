"""Geocode ONLY voters who appear in election rolls but aren't geocoded yet.
These are priority voters — they actually voted but we don't have their coordinates.

Collects VUIDs from map_data files, cross-references with DB, and geocodes
only the ungeocoded ones using their registration address."""
import json
import sys
import time
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, '/opt/whovoted/backend')
from config import Config, setup_logging
from geocoder import GeocodingCache, NominatimGeocoder
import database as db

logger = setup_logging()
STATUS_FILE = Config.DATA_DIR / 'geocode_registry_status.json'

def write_status(status):
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception:
        pass

def run():
    db.init_db()
    conn = db.get_connection()
    data_dir = Config.PUBLIC_DIR / 'data'

    # Step 1: Collect VUIDs from election files
    print("Collecting VUIDs from election voter rolls...")
    election_vuids = set()
    for f in sorted(data_dir.glob('map_data_*.json')):
        try:
            with open(f, 'r') as fh:
                geojson = json.load(fh)
            for feature in geojson.get('features', []):
                props = feature.get('properties', {})
                vuid = str(props.get('vuid', '')).strip()
                if not vuid or vuid == 'nan':
                    continue
                if vuid.endswith('.0'):
                    vuid = vuid[:-2]
                if len(vuid) == 10 and vuid.isdigit():
                    election_vuids.add(vuid)
        except Exception:
            pass
    print(f"Total unique VUIDs from elections: {len(election_vuids):,}")

    # Step 2: Find which of these are ungeocoded in the DB
    ungeocoded = []
    for vuid in election_vuids:
        row = conn.execute(
            "SELECT vuid, address FROM voters WHERE vuid = ? AND geocoded = 0 AND address != ''",
            (vuid,)
        ).fetchone()
        if row:
            ungeocoded.append((row[0], row[1]))

    print(f"Ungeocoded voters who voted: {len(ungeocoded):,}")
    if not ungeocoded:
        print("Nothing to geocode!")
        return

    # Deduplicate by address
    addr_to_vuids = {}
    for vuid, address in ungeocoded:
        key = address.strip().upper()
        addr_to_vuids.setdefault(key, []).append(vuid)
    
    unique_addrs = list(addr_to_vuids.keys())
    print(f"Unique addresses to geocode: {len(unique_addrs):,}")

    # Step 3: Geocode
    cache = GeocodingCache(str(Config.GEOCODING_CACHE_FILE))
    geocoder = NominatimGeocoder(cache)
    
    status = {
        'running': True,
        'county': 'Hidalgo',
        'total_to_geocode': len(ungeocoded),
        'unique_addresses': len(unique_addrs),
        'processed': 0,
        'geocoded': 0,
        'failed': 0,
        'started_at': datetime.now().isoformat()
    }
    write_status(status)

    geocoded_count = 0
    failed_count = 0
    processed_addrs = 0
    start_time = time.time()
    batch_size = 20
    max_workers = 5

    for i in range(0, len(unique_addrs), batch_size):
        batch = unique_addrs[i:i + batch_size]
        results = {}

        def geocode_one(addr):
            try:
                return addr, geocoder.geocode(addr)
            except Exception as e:
                logger.warning(f"Geocode error: {e}")
                return addr, None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(geocode_one, a): a for a in batch}
            for future in as_completed(futures):
                addr, result = future.result()
                results[addr] = result

        now = datetime.now().isoformat()
        for addr, result in results.items():
            vuids = addr_to_vuids[addr]
            if result and result.get('lat') and result.get('lng'):
                lat, lng = result['lat'], result['lng']
                placeholders = ','.join('?' * len(vuids))
                conn.execute(
                    f"UPDATE voters SET lat=?, lng=?, geocoded=1, updated_at=? WHERE vuid IN ({placeholders})",
                    [lat, lng, now] + vuids
                )
                conn.execute("""
                    INSERT INTO geocoding_cache (address_key, lat, lng, display_name, source, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(address_key) DO UPDATE SET lat=excluded.lat, lng=excluded.lng
                """, (addr, lat, lng, result.get('display_name', ''), 'priority_geocode', now))
                geocoded_count += len(vuids)
            else:
                failed_count += len(vuids)
                placeholders = ','.join('?' * len(vuids))
                conn.execute(
                    f"UPDATE voters SET geocoded=-1, updated_at=? WHERE vuid IN ({placeholders})",
                    [now] + vuids
                )

        conn.commit()
        processed_addrs += len(batch)
        elapsed = time.time() - start_time
        rate = processed_addrs / elapsed if elapsed > 0 else 0
        remaining = (len(unique_addrs) - processed_addrs) / rate if rate > 0 else 0

        status.update({
            'processed': geocoded_count + failed_count,
            'geocoded': geocoded_count,
            'failed': failed_count,
            'addresses_done': processed_addrs,
            'rate': round(rate, 1),
            'elapsed_seconds': round(elapsed),
            'estimated_remaining_seconds': round(remaining),
            'last_update': datetime.now().isoformat()
        })
        write_status(status)
        print(f"  Addrs: {processed_addrs:,}/{len(unique_addrs):,} | "
              f"Voters geocoded: {geocoded_count:,} | Failed: {failed_count:,} | "
              f"Rate: {rate:.1f} addr/s | ETA: {remaining/60:.1f}m")

    cache.save_cache()
    elapsed = time.time() - start_time
    status.update({
        'running': False,
        'completed_at': datetime.now().isoformat(),
        'elapsed_seconds': round(elapsed)
    })
    write_status(status)

    # Final stats
    total = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo'").fetchone()[0]
    geo = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded=1 AND county='Hidalgo'").fetchone()[0]
    print(f"\n{'='*50}")
    print(f"DONE: {geocoded_count:,} voters geocoded, {failed_count:,} failed")
    print(f"DB: {geo:,}/{total:,} geocoded ({geo/total*100:.1f}%)")
    print(f"Time: {elapsed:.0f}s")

if __name__ == '__main__':
    run()
