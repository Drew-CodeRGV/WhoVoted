#!/usr/bin/env python3
"""Audit data coverage: compare what's in GeoJSON files vs what's in the DB.

Identifies any data that exists ONLY in GeoJSON and would be lost if we
switch to DB-only serving. Also checks geocoding coverage.
"""
import json
import sqlite3
from pathlib import Path
from collections import defaultdict

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = Path('/opt/whovoted/data')
PUBLIC_DIR = Path('/opt/whovoted/public/data')

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("DATA COVERAGE AUDIT")
print("=" * 70)

# 1. DB voter table stats
print("\n--- VOTERS TABLE ---")
total_voters = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded=1").fetchone()[0]
has_name = conn.execute("SELECT COUNT(*) FROM voters WHERE (firstname IS NOT NULL AND firstname != '') OR (lastname IS NOT NULL AND lastname != '')").fetchone()[0]
has_address = conn.execute("SELECT COUNT(*) FROM voters WHERE address IS NOT NULL AND address != ''").fetchone()[0]
has_precinct = conn.execute("SELECT COUNT(*) FROM voters WHERE precinct IS NOT NULL AND precinct != ''").fetchone()[0]
has_sex = conn.execute("SELECT COUNT(*) FROM voters WHERE sex IS NOT NULL AND sex != ''").fetchone()[0]
has_birth_year = conn.execute("SELECT COUNT(*) FROM voters WHERE birth_year IS NOT NULL AND birth_year > 0").fetchone()[0]
has_party = conn.execute("SELECT COUNT(*) FROM voters WHERE current_party IS NOT NULL AND current_party != ''").fetchone()[0]
print(f"  Total voters:     {total_voters:,}")
print(f"  Geocoded:         {geocoded:,} ({100*geocoded/total_voters:.1f}%)")
print(f"  Has name:         {has_name:,}")
print(f"  Has address:      {has_address:,}")
print(f"  Has precinct:     {has_precinct:,}")
print(f"  Has sex:          {has_sex:,}")
print(f"  Has birth_year:   {has_birth_year:,}")
print(f"  Has party:        {has_party:,}")

# Check for lat/lng without geocoded flag
has_coords_no_flag = conn.execute(
    "SELECT COUNT(*) FROM voters WHERE lat IS NOT NULL AND lng IS NOT NULL AND geocoded != 1"
).fetchone()[0]
if has_coords_no_flag:
    print(f"  ⚠️  Has coords but geocoded!=1: {has_coords_no_flag:,}")

# 2. voter_elections table stats
print("\n--- VOTER_ELECTIONS TABLE ---")
total_records = conn.execute("SELECT COUNT(*) FROM voter_elections").fetchone()[0]
unique_vuids = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections").fetchone()[0]
elections = conn.execute(
    "SELECT election_date, party_voted, voting_method, COUNT(*) as cnt "
    "FROM voter_elections GROUP BY election_date, party_voted, voting_method "
    "ORDER BY election_date, party_voted"
).fetchall()
print(f"  Total records:    {total_records:,}")
print(f"  Unique VUIDs:     {unique_vuids:,}")
print(f"  Elections:")
for e in elections:
    print(f"    {e['election_date']} | {e['party_voted']:12s} | {e['voting_method']:15s} | {e['cnt']:,} voters")

# 3. Check VUIDs in voter_elections that are NOT in voters table
orphan_vuids = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid) FROM voter_elections ve
    LEFT JOIN voters v ON ve.vuid = v.vuid
    WHERE v.vuid IS NULL
""").fetchone()[0]
print(f"\n  Orphan VUIDs (in elections but not in voters): {orphan_vuids:,}")

# 4. Scan GeoJSON files and compare
print("\n--- GEOJSON FILES vs DB ---")
geojson_files = sorted(DATA_DIR.glob('map_data_*.json'))
for gf in geojson_files:
    with open(gf) as f:
        data = json.load(f)
    features = data.get('features', [])
    if not features:
        continue
    
    # Sample properties from first feature
    sample_props = features[0].get('properties', {})
    prop_keys = sorted(sample_props.keys())
    
    # Count VUIDs in GeoJSON
    geojson_vuids = set()
    geojson_with_coords = 0
    geojson_with_name = 0
    geojson_only_coords = []  # VUIDs that have coords in GeoJSON but not in DB
    
    for feat in features:
        props = feat.get('properties', {})
        vuid = props.get('vuid', '')
        if vuid:
            geojson_vuids.add(vuid)
        geom = feat.get('geometry')
        if geom and geom.get('coordinates'):
            geojson_with_coords += 1
        if props.get('name', '').strip() or props.get('firstname', '').strip():
            geojson_with_name += 1
    
    # Check which GeoJSON VUIDs are missing from DB
    if geojson_vuids:
        missing_from_db = set()
        geojson_has_coords_db_doesnt = 0
        vuids_list = list(geojson_vuids)
        for i in range(0, len(vuids_list), 999):
            chunk = vuids_list[i:i+999]
            ph = ','.join('?' * len(chunk))
            db_rows = conn.execute(
                f"SELECT vuid, geocoded, lat, lng FROM voters WHERE vuid IN ({ph})", chunk
            ).fetchall()
            db_map = {r['vuid']: r for r in db_rows}
            for v in chunk:
                if v not in db_map:
                    missing_from_db.add(v)
        
        # Check coords coverage
        for feat in features:
            props = feat.get('properties', {})
            vuid = props.get('vuid', '')
            geom = feat.get('geometry')
            if vuid and geom and geom.get('coordinates'):
                coords = geom['coordinates']
                # Check if DB has these coords
                db_row = conn.execute(
                    "SELECT lat, lng, geocoded FROM voters WHERE vuid = ?", (vuid,)
                ).fetchone()
                if db_row and (db_row['geocoded'] != 1 or db_row['lat'] is None):
                    geojson_only_coords.append({
                        'vuid': vuid,
                        'lat': coords[1],
                        'lng': coords[0],
                    })
                    if len(geojson_only_coords) >= 5:
                        break  # Just sample a few
    
    print(f"\n  {gf.name}:")
    print(f"    Features: {len(features):,}")
    print(f"    With coords: {geojson_with_coords:,}")
    print(f"    With names: {geojson_with_name:,}")
    print(f"    Unique VUIDs: {len(geojson_vuids):,}")
    if geojson_vuids:
        print(f"    Missing from DB: {len(missing_from_db):,}")
    if geojson_only_coords:
        print(f"    ⚠️  Has coords in GeoJSON but NOT in DB: {len(geojson_only_coords)}+ (sampled)")
        for item in geojson_only_coords[:3]:
            print(f"       VUID {item['vuid']}: ({item['lat']}, {item['lng']})")
    print(f"    Properties: {', '.join(prop_keys)}")

# 5. Check geocoding_cache table
print("\n--- GEOCODING CACHE ---")
cache_count = conn.execute("SELECT COUNT(*) FROM geocoding_cache").fetchone()[0]
print(f"  Cached addresses: {cache_count:,}")

# 6. Check for any JSON cache files
json_caches = list(DATA_DIR.glob('*cache*.json'))
print(f"  JSON cache files: {len(json_caches)}")
for jc in json_caches:
    size_mb = jc.stat().st_size / (1024*1024)
    print(f"    {jc.name}: {size_mb:.1f} MB")

conn.close()
print("\n" + "=" * 70)
print("AUDIT COMPLETE")
print("=" * 70)
