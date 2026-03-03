"""Post-import pipeline for voter registry uploads.

After a county's voter registration file is imported, this module runs:
1. Backfill geocoded coords from existing map_data files
2. Import election history from map_data + metadata files for that county
3. Update current_party from election history
4. Kick off priority geocoding for voters who voted but aren't geocoded

All functions are county-aware and can be called independently or as a pipeline.
"""
import json
import gc
import logging
import time
from datetime import datetime
from pathlib import Path

from config import Config
import database as db

logger = logging.getLogger(__name__)


def run_pipeline(county: str, log_fn=None):
    """Run the full post-import pipeline for a county.
    
    Args:
        county: County name (e.g. 'Hidalgo')
        log_fn: Optional callback for status messages (str -> None)
    """
    def log(msg):
        logger.info(f"[PostImport:{county}] {msg}")
        if log_fn:
            log_fn(msg)

    log("Starting post-import pipeline")
    start = time.time()

    # Step 1: Backfill geocoded coords from map_data
    log("Step 1/4: Backfilling geocoded coordinates from election data...")
    backfilled = backfill_coords_for_county(county, log)

    # Step 2: Import election history
    log("Step 2/4: Importing election history...")
    election_records = import_election_history_for_county(county, log)

    # Step 3: Update current_party
    log("Step 3/4: Updating party affiliations...")
    party_updated = update_parties_for_county(county, log)

    # Step 4: Queue priority geocoding (non-blocking summary)
    log("Step 4/4: Checking priority geocoding needs...")
    priority_stats = check_priority_geocoding(county, log)

    # Step 5: Generate county report caches
    log("Step 5/5: Generating county report caches...")
    cache_count = generate_county_report_caches(county, log)

    elapsed = time.time() - start
    log(f"Post-import pipeline complete in {elapsed:.1f}s — "
        f"{backfilled} coords backfilled, {election_records} election records, "
        f"{party_updated} parties updated, {priority_stats['need_geocoding']} voters need geocoding, "
        f"{cache_count} report caches generated")

    return {
        'backfilled': backfilled,
        'election_records': election_records,
        'party_updated': party_updated,
        'priority_geocoding': priority_stats,
        'cache_count': cache_count,
        'elapsed_seconds': round(elapsed, 1)
    }


def backfill_coords_for_county(county: str, log=None):
    """Pull geocoded coords from map_data GeoJSON files into voter DB for a specific county.
    
    Scans map_data files, matches VUIDs to voters in the given county,
    and updates their lat/lng if they aren't already geocoded.
    """
    if log is None:
        log = lambda msg: None

    data_dir = Config.PUBLIC_DIR / 'data'
    geocoded_vuids = {}  # vuid -> (lat, lng)

    for f in sorted(data_dir.glob('map_data_*.json')):
        try:
            # Check if this file belongs to the county via metadata
            meta_name = 'metadata_' + f.name[len('map_data_'):]
            meta_path = data_dir / meta_name
            if meta_path.exists():
                with open(meta_path, 'r') as mf:
                    meta = json.load(mf)
                file_county = meta.get('county', '')
                if file_county and file_county.lower() != county.lower():
                    continue

            with open(f, 'r') as fh:
                geojson = json.load(fh)
            count = 0
            for feature in geojson.get('features', []):
                props = feature.get('properties', {})
                geom = feature.get('geometry')
                if not geom:
                    continue
                coords = geom.get('coordinates', [])
                vuid = str(props.get('vuid', '')).strip()
                if not vuid:
                    vuid = str(props.get('cert', '')).strip()
                if vuid.endswith('.0'):
                    vuid = vuid[:-2]
                if vuid and len(coords) >= 2:
                    lng, lat = float(coords[0]), float(coords[1])
                    if lat != 0 and lng != 0:
                        geocoded_vuids[vuid] = (lat, lng)
                        count += 1
            log(f"  {f.name}: {count} VUIDs with coordinates")
            del geojson
            gc.collect()
        except Exception as e:
            log(f"  {f.name}: ERROR {e}")

    if not geocoded_vuids:
        log("No geocoded VUIDs found in map_data files")
        return 0

    log(f"Found {len(geocoded_vuids):,} unique geocoded VUIDs — updating DB...")

    conn = db.get_connection()
    updated = 0
    now = datetime.now().isoformat()
    batch_size = 500
    items = list(geocoded_vuids.items())

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        for vuid, (lat, lng) in batch:
            cursor = conn.execute(
                "UPDATE voters SET lat = ?, lng = ?, geocoded = 1, updated_at = ? "
                "WHERE vuid = ? AND geocoded = 0 AND county = ?",
                (lat, lng, now, vuid, county)
            )
            updated += cursor.rowcount
        conn.commit()

    log(f"Backfill complete: {updated:,} voter records updated with coordinates")
    del geocoded_vuids
    gc.collect()
    return updated


def import_election_history_for_county(county: str, log=None):
    """Import election participation records from map_data files for a specific county."""
    if log is None:
        log = lambda msg: None

    data_dir = Config.PUBLIC_DIR / 'data'
    total_records = 0
    total_files = 0

    for meta_file in sorted(data_dir.glob('metadata_*.json')):
        try:
            with open(meta_file, 'r') as f:
                meta = json.load(f)
            if not meta or meta.get('is_cumulative'):
                continue

            # Filter by county
            file_county = meta.get('county', '')
            if file_county and file_county.lower() != county.lower():
                continue

            election_date = meta.get('election_date', '')
            election_year = meta.get('year', '')
            election_type = meta.get('election_type', '')
            voting_method = meta.get('voting_method', '')
            primary_party = meta.get('primary_party', '')
            source_file = meta.get('original_filename', meta_file.name)

            party_voted = ''
            if primary_party:
                if 'dem' in primary_party.lower():
                    party_voted = 'Democratic'
                elif 'rep' in primary_party.lower():
                    party_voted = 'Republican'

            map_data_name = 'map_data_' + meta_file.name[len('metadata_'):]
            map_data_path = data_dir / map_data_name
            if not map_data_path.exists():
                continue

            with open(map_data_path, 'r') as f:
                geojson = json.load(f)

            features = geojson.get('features', [])
            batch = []
            file_count = 0

            for feature in features:
                props = feature.get('properties', {})
                vuid = str(props.get('vuid', '')).strip()
                if not vuid or vuid == 'nan':
                    continue
                if vuid.endswith('.0'):
                    vuid = vuid[:-2]
                if not (len(vuid) == 10 and vuid.isdigit()):
                    continue

                precinct = str(props.get('precinct', '')).strip()
                ballot_style = str(props.get('ballot_style', '')).strip()
                site = str(props.get('site', '')).strip()
                check_in = str(props.get('check_in', '')).strip()

                voter_party = party_voted
                if not voter_party:
                    pac = str(props.get('party_affiliation_current', '')).strip()
                    if pac:
                        voter_party = pac

                batch.append({
                    'vuid': vuid,
                    'election_date': election_date,
                    'election_year': election_year,
                    'election_type': election_type,
                    'voting_method': voting_method,
                    'party_voted': voter_party,
                    'precinct': precinct,
                    'ballot_style': ballot_style,
                    'site': site,
                    'check_in': check_in,
                    'source_file': source_file
                })
                file_count += 1

                if len(batch) >= 500:
                    db.record_elections_batch(batch)
                    batch = []

            if batch:
                db.record_elections_batch(batch)

            total_records += file_count
            total_files += 1
            vm_label = 'EV' if 'early' in voting_method.lower() else 'ED'
            log(f"  {meta_file.name}: {file_count:,} records ({election_date} {party_voted} {vm_label})")

            del geojson
            gc.collect()

        except Exception as e:
            log(f"  {meta_file.name}: ERROR {e}")

    log(f"Election history: {total_records:,} records from {total_files} files")
    return total_records


def update_parties_for_county(county: str, log=None):
    """Update current_party for voters in a county based on their most recent election."""
    if log is None:
        log = lambda msg: None

    conn = db.get_connection()

    # Update current_party from most recent election participation
    cursor = conn.execute("""
        UPDATE voters SET current_party = (
            SELECT ve.party_voted
            FROM voter_elections ve
            WHERE ve.vuid = voters.vuid
              AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
            ORDER BY ve.election_date DESC
            LIMIT 1
        ), updated_at = ?
        WHERE county = ?
          AND vuid IN (
            SELECT DISTINCT vuid FROM voter_elections
            WHERE party_voted != '' AND party_voted IS NOT NULL
          )
    """, (datetime.now().isoformat(), county))

    updated = cursor.rowcount
    conn.commit()
    log(f"Updated current_party for {updated:,} voters in {county} County")
    return updated


def check_priority_geocoding(county: str, log=None):
    """Check how many voters who voted still need geocoding. Returns stats dict."""
    if log is None:
        log = lambda msg: None

    conn = db.get_connection()

    # Voters in this county who appear in election rolls but aren't geocoded
    result = conn.execute("""
        SELECT COUNT(DISTINCT v.vuid)
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.county = ? AND v.geocoded = 0 AND v.address != ''
    """, (county,)).fetchone()
    need_geocoding = result[0] if result else 0

    total_voted = conn.execute("""
        SELECT COUNT(DISTINCT v.vuid)
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.county = ?
    """, (county,)).fetchone()
    total = total_voted[0] if total_voted else 0

    geocoded_voted = total - need_geocoding

    stats = {
        'total_voted': total,
        'geocoded': geocoded_voted,
        'need_geocoding': need_geocoding
    }

    if total > 0:
        pct = geocoded_voted / total * 100
        log(f"Priority geocoding: {geocoded_voted:,}/{total:,} voters who voted are geocoded ({pct:.1f}%), "
            f"{need_geocoding:,} still need geocoding")
    else:
        log(f"No election participation records found for {county} County")

    return stats



def generate_county_report_caches(county: str, log=None):
    """Generate county report cache files for all elections in this county."""
    if log is None:
        log = lambda msg: None
    
    import reports
    
    conn = db.get_connection()
    
    # Get all election_date + voting_method combinations for this county
    elections = conn.execute("""
        SELECT DISTINCT ve.election_date, ve.voting_method, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        GROUP BY ve.election_date, ve.voting_method
        HAVING cnt > 0
        ORDER BY ve.election_date DESC
    """, (county,)).fetchall()
    
    if not elections:
        log(f"  No elections found for {county} County")
        return 0
    
    cache_dir = Config.PUBLIC_DIR / 'cache'
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    cache_count = 0
    for row in elections:
        election_date = row[0]
        voting_method = row[1]
        voter_count = row[2]
        
        try:
            # Generate the report data
            report_data = reports.generate_county_report_data(county, election_date, voting_method)
            
            # Save to cache file
            method_str = voting_method or 'all'
            cache_file = cache_dir / f'county_report_{county}_{election_date}_{method_str}.json'
            
            with open(cache_file, 'w') as f:
                json.dump(report_data, f, separators=(',', ':'))
            
            cache_count += 1
            log(f"  ✓ {election_date} {voting_method}: {voter_count} voters")
            
        except Exception as e:
            log(f"  ✗ {election_date} {voting_method}: ERROR {e}")
    
    log(f"Generated {cache_count} county report caches for {county} County")
    return cache_count
