"""Check VUIDs from election voter rolls against the registration DB.
Find voters who voted but whose addresses haven't been geocoded yet.
These are the priority voters to geocode — they actually showed up to vote."""
import json
import sys
from collections import defaultdict

sys.path.insert(0, '/opt/whovoted/backend')
from config import Config
import sqlite3

db_path = Config.DATA_DIR / 'whovoted.db'
conn = sqlite3.connect(str(db_path))
data_dir = Config.PUBLIC_DIR / 'data'

# Collect all unique VUIDs from election files, stripping .0
print("Scanning election voter rolls (map_data files)...")
election_vuids = set()
vuids_per_file = {}

for f in sorted(data_dir.glob('map_data_*.json')):
    try:
        with open(f, 'r') as fh:
            geojson = json.load(fh)
        file_vuids = set()
        for feature in geojson.get('features', []):
            props = feature.get('properties', {})
            vuid = str(props.get('vuid', '')).strip()
            if not vuid or vuid == 'nan':
                continue
            if vuid.endswith('.0'):
                vuid = vuid[:-2]
            if len(vuid) == 10 and vuid.isdigit():
                file_vuids.add(vuid)
                election_vuids.add(vuid)
        vuids_per_file[f.name] = len(file_vuids)
        print(f"  {f.name}: {len(file_vuids):,} VUIDs")
    except Exception as e:
        print(f"  {f.name}: ERROR {e}")

print(f"\nTotal unique VUIDs across all election files: {len(election_vuids):,}")

# Check each VUID against the DB
print("\nChecking against voter registry DB...")
in_db_geocoded = 0
in_db_not_geocoded = 0
not_in_db = 0
not_in_db_samples = []

for vuid in election_vuids:
    row = conn.execute("SELECT geocoded, address FROM voters WHERE vuid = ?", (vuid,)).fetchone()
    if row is None:
        not_in_db += 1
        if len(not_in_db_samples) < 10:
            not_in_db_samples.append(vuid)
    elif row[0] == 1:
        in_db_geocoded += 1
    else:
        in_db_not_geocoded += 1

total_voted = len(election_vuids)
print(f"\n{'='*60}")
print(f"ELECTION VOTER ROLL COVERAGE REPORT")
print(f"{'='*60}")
print(f"Total unique voters who voted:        {total_voted:,}")
print(f"  In registry DB + geocoded:          {in_db_geocoded:,} ({in_db_geocoded/total_voted*100:.1f}%)")
print(f"  In registry DB + NOT geocoded:      {in_db_not_geocoded:,} ({in_db_not_geocoded/total_voted*100:.1f}%)")
print(f"  NOT in registry DB at all:          {not_in_db:,} ({not_in_db/total_voted*100:.1f}%)")
print(f"{'='*60}")

if in_db_not_geocoded > 0:
    # Get the addresses for these voters
    print(f"\nThese {in_db_not_geocoded:,} voters have registration addresses that need geocoding.")
    rows = conn.execute("""
        SELECT vuid, address, city, zip FROM voters 
        WHERE geocoded = 0 AND vuid IN (
            SELECT vuid FROM voters WHERE geocoded = 0
        )
        LIMIT 10
    """).fetchall()
    print("Sample addresses:")
    for r in rows[:10]:
        print(f"  VUID {r[0]}: {r[1]} {r[2]} {r[3]}")

if not_in_db > 0:
    print(f"\n{not_in_db:,} voters voted but are NOT in the Hidalgo registration file.")
    print("Sample VUIDs not in DB:")
    for v in not_in_db_samples:
        print(f"  {v}")

# Count unique addresses for the ungeocoded voters who voted
ungeocoded_voted_addrs = conn.execute("""
    SELECT COUNT(DISTINCT address) FROM voters 
    WHERE geocoded = 0 AND address != '' AND address IS NOT NULL
    AND vuid IN ({})
""".format(','.join('?' * min(len(election_vuids), 50000))), 
    list(election_vuids)[:50000]).fetchone()[0]
print(f"\nUnique addresses for ungeocoded voters who voted: {ungeocoded_voted_addrs:,}")

conn.close()
