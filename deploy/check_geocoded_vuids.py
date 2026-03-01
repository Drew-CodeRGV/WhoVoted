"""Check how many VUIDs in the voter registry DB already have geocoded addresses
in the existing map_data GeoJSON files."""
import json
import sys
from pathlib import Path

sys.path.insert(0, '/opt/whovoted/backend')
from config import Config

data_dir = Config.PUBLIC_DIR / 'data'

# Collect all unique VUIDs with coordinates from map_data files
geocoded_vuids = {}  # vuid -> (lat, lng)

for f in sorted(data_dir.glob('map_data_*.json')):
    try:
        with open(f, 'r') as fh:
            geojson = json.load(fh)
        count = 0
        for feature in geojson.get('features', []):
            props = feature.get('properties', {})
            coords = feature.get('geometry', {}).get('coordinates', [])
            vuid = str(props.get('vuid', '')).strip()
            if not vuid:
                vuid = str(props.get('cert', '')).strip()
            if vuid and len(coords) >= 2:
                lng, lat = coords[0], coords[1]
                if lat and lng:
                    geocoded_vuids[vuid] = (lat, lng)
                    count += 1
        print(f"  {f.name}: {count} VUIDs with coords")
    except Exception as e:
        print(f"  {f.name}: ERROR {e}")

print(f"\nTotal unique geocoded VUIDs from map_data files: {len(geocoded_vuids):,}")

# Now check against the voter registry DB
import sqlite3
db_path = Config.DATA_DIR / 'whovoted.db'
conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row

total_voters = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
already_geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded = 1").fetchone()[0]

print(f"\nVoter registry DB:")
print(f"  Total voters: {total_voters:,}")
print(f"  Already geocoded in DB: {already_geocoded:,}")

# Check overlap
vuids_in_db = set()
cursor = conn.execute("SELECT vuid FROM voters")
for row in cursor:
    vuids_in_db.add(row[0])

matched = geocoded_vuids.keys() & vuids_in_db
not_in_db = geocoded_vuids.keys() - vuids_in_db

print(f"\nCross-reference:")
print(f"  VUIDs in map_data that match registry DB: {len(matched):,}")
print(f"  VUIDs in map_data NOT in registry DB: {len(not_in_db):,}")
print(f"  Registry voters with existing geocoded coords: {len(matched):,} / {total_voters:,} ({len(matched)/total_voters*100:.1f}%)")
print(f"  Registry voters still needing geocoding: {total_voters - len(matched):,} ({(total_voters - len(matched))/total_voters*100:.1f}%)")

# Also check the geocoding cache
cache_path = Config.DATA_DIR / 'geocoded_addresses.json'
if cache_path.exists():
    with open(cache_path, 'r') as f:
        cache = json.load(f)
    print(f"\nGeocoding cache (JSON): {len(cache):,} cached addresses")

cache_count = conn.execute("SELECT COUNT(*) FROM geocoding_cache").fetchone()[0]
print(f"Geocoding cache (SQLite): {cache_count:,} cached addresses")

conn.close()
