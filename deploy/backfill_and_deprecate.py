#!/usr/bin/env python3
"""Backfill missing voter data from GeoJSON files into the DB, then
move legacy files to a deprecated/ folder (not deleted).

Phase 1: Backfill voters from GeoJSON that are missing from the voters table
Phase 2: Backfill geocoded coords from GeoJSON for voters that exist but lack coords
Phase 3: Migrate JSON geocoding cache into DB cache table
Phase 4: Move GeoJSON + metadata + JSON cache files to deprecated/
"""
import json
import sqlite3
import shutil
from pathlib import Path
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = Path('/opt/whovoted/data')
PUBLIC_DIR = Path('/opt/whovoted/public/data')
DEPRECATED_DIR = DATA_DIR / 'deprecated'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("BACKFILL & DEPRECATE")
print("=" * 70)

# ── Phase 1: Backfill missing voters from GeoJSON ──
print("\n--- Phase 1: Backfill missing voters ---")

geojson_files = sorted(DATA_DIR.glob('map_data_*.json'))
inserted_voters = 0
updated_coords = 0

for gf in geojson_files:
    if 'cumulative' in gf.name:
        continue  # Skip cumulative (duplicates of day snapshots)
    
    with open(gf) as f:
        data = json.load(f)
    
    features = data.get('features', [])
    if not features:
        continue
    
    print(f"\n  Processing {gf.name} ({len(features):,} features)...")
    
    # Determine county from filename
    parts = gf.stem.split('_')
    # map_data_Hidalgo_2016_primary_democratic_20160301_ev
    county = parts[2] if len(parts) > 2 else 'Hidalgo'
    
    batch_insert = []
    batch_update_coords = []
    
    for feat in features:
        props = feat.get('properties', {})
        geom = feat.get('geometry')
        vuid = str(props.get('vuid', '')).strip()
        if not vuid or not vuid.isdigit():
            continue
        
        # Check if voter exists in DB
        existing = conn.execute("SELECT vuid, geocoded, lat, lng FROM voters WHERE vuid = ?", (vuid,)).fetchone()
        
        lat = None
        lng = None
        if geom and geom.get('coordinates'):
            coords = geom['coordinates']
            lng = coords[0]
            lat = coords[1]
        
        if not existing:
            # Insert new voter from GeoJSON data
            firstname = str(props.get('firstname', '')).strip()
            lastname = str(props.get('lastname', '')).strip()
            middlename = str(props.get('middlename', '')).strip()
            address = str(props.get('address', '') or props.get('original_address', '')).strip()
            precinct = str(props.get('precinct', '')).strip()
            sex = str(props.get('sex', '')).strip()
            birth_year = props.get('birth_year', 0) or 0
            if isinstance(birth_year, str):
                try:
                    birth_year = int(birth_year)
                except:
                    birth_year = 0
            current_party = str(props.get('party_affiliation_current', '') or props.get('party', '')).strip()
            
            batch_insert.append((
                vuid, lastname, firstname, middlename, '', address, '', '',
                county, birth_year, '', sex, '', current_party, precinct,
                lat, lng, 1 if lat is not None else 0,
                'geojson_backfill', datetime.now().isoformat()
            ))
        elif existing and lat is not None and (existing['geocoded'] != 1 or existing['lat'] is None):
            # Voter exists but lacks coords — backfill from GeoJSON
            batch_update_coords.append((lat, lng, 1, datetime.now().isoformat(), vuid))
    
    # Execute batch insert
    if batch_insert:
        conn.executemany(
            "INSERT OR IGNORE INTO voters "
            "(vuid, lastname, firstname, middlename, suffix, address, city, zip, "
            "county, birth_year, registration_date, sex, registered_party, current_party, "
            "precinct, lat, lng, geocoded, source, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            batch_insert
        )
        inserted_voters += len(batch_insert)
        print(f"    Inserted {len(batch_insert):,} new voters")
    
    # Execute batch coord updates
    if batch_update_coords:
        conn.executemany(
            "UPDATE voters SET lat=?, lng=?, geocoded=?, updated_at=? WHERE vuid=?",
            batch_update_coords
        )
        updated_coords += len(batch_update_coords)
        print(f"    Updated coords for {len(batch_update_coords):,} voters")

conn.commit()
print(f"\n  Total: {inserted_voters:,} voters inserted, {updated_coords:,} coords updated")

# ── Phase 2: Migrate JSON geocoding cache to DB ──
print("\n--- Phase 2: Migrate JSON geocoding cache ---")
json_cache_path = DATA_DIR / 'geocoding_cache.json'
if json_cache_path.exists():
    with open(json_cache_path) as f:
        json_cache = json.load(f)
    
    # Check current DB cache count
    db_cache_count = conn.execute("SELECT COUNT(*) FROM geocoding_cache").fetchone()[0]
    print(f"  JSON cache entries: {len(json_cache):,}")
    print(f"  DB cache entries:   {db_cache_count:,}")
    
    migrated = 0
    batch = []
    for addr_key, entry in json_cache.items():
        if isinstance(entry, dict):
            lat = entry.get('lat')
            lng = entry.get('lng') or entry.get('lon')
            display = entry.get('display_name', '') or entry.get('address', '') or addr_key
            source = entry.get('source', 'json_cache')
        elif isinstance(entry, (list, tuple)) and len(entry) >= 2:
            lat, lng = entry[0], entry[1]
            display = addr_key
            source = 'json_cache'
        else:
            continue
        
        if lat is not None and lng is not None:
            batch.append((addr_key.strip().upper(), lat, lng, display, source, datetime.now().isoformat()))
            if len(batch) >= 1000:
                conn.executemany(
                    "INSERT OR IGNORE INTO geocoding_cache "
                    "(address_key, lat, lng, display_name, source, cached_at) "
                    "VALUES (?,?,?,?,?,?)",
                    batch
                )
                migrated += len(batch)
                batch = []
    
    if batch:
        conn.executemany(
            "INSERT OR IGNORE INTO geocoding_cache "
            "(address_key, lat, lng, display_name, source, cached_at) "
            "VALUES (?,?,?,?,?,?)",
            batch
        )
        migrated += len(batch)
    
    conn.commit()
    new_count = conn.execute("SELECT COUNT(*) FROM geocoding_cache").fetchone()[0]
    print(f"  Migrated {migrated:,} entries, DB cache now: {new_count:,}")
else:
    print("  No JSON cache file found")

# ── Phase 3: Verify no data loss ──
print("\n--- Phase 3: Verification ---")
total_voters = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded=1").fetchone()[0]
orphans = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid) FROM voter_elections ve
    LEFT JOIN voters v ON ve.vuid = v.vuid
    WHERE v.vuid IS NULL
""").fetchone()[0]
print(f"  Total voters:  {total_voters:,}")
print(f"  Geocoded:      {geocoded:,}")
print(f"  Orphan VUIDs:  {orphans:,}")

if orphans > 0:
    print(f"  ⚠️  {orphans} VUIDs still in voter_elections but not in voters")
    # Show sample orphans
    sample = conn.execute("""
        SELECT DISTINCT ve.vuid, ve.election_date, ve.party_voted
        FROM voter_elections ve
        LEFT JOIN voters v ON ve.vuid = v.vuid
        WHERE v.vuid IS NULL
        LIMIT 5
    """).fetchall()
    for s in sample:
        print(f"     {s['vuid']} | {s['election_date']} | {s['party_voted']}")

# ── Phase 4: Move legacy files to deprecated/ ──
print("\n--- Phase 4: Deprecate legacy files ---")
DEPRECATED_DIR.mkdir(parents=True, exist_ok=True)
DEPRECATED_PUBLIC = PUBLIC_DIR.parent / 'deprecated_data'
DEPRECATED_PUBLIC.mkdir(parents=True, exist_ok=True)

moved_count = 0

# Move GeoJSON and metadata from data/
for pattern in ['map_data_*.json', 'metadata_*.json', 'geocoding_cache.json', 'geocoded_addresses.json', 'map_data.json']:
    for f in DATA_DIR.glob(pattern):
        dest = DEPRECATED_DIR / f.name
        shutil.move(str(f), str(dest))
        moved_count += 1
        print(f"  data/ → deprecated/: {f.name}")

# Move GeoJSON and metadata from public/data/
for pattern in ['map_data_*.json', 'metadata_*.json']:
    for f in PUBLIC_DIR.glob(pattern):
        dest = DEPRECATED_PUBLIC / f.name
        shutil.move(str(f), str(dest))
        moved_count += 1
        print(f"  public/data/ → deprecated_data/: {f.name}")

print(f"\n  Moved {moved_count} files to deprecated folders")

conn.close()
print("\n" + "=" * 70)
print("BACKFILL & DEPRECATE COMPLETE")
print("DB is now the single source of truth.")
print("Legacy files preserved in deprecated/ folders.")
print("=" * 70)
