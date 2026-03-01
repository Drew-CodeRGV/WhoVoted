"""Audit VUID formats between the voter registry DB and the map_data election files.
Check for padding/format mismatches that prevent matching."""
import json
import sys
from pathlib import Path
from collections import Counter

sys.path.insert(0, '/opt/whovoted/backend')
from config import Config

data_dir = Config.PUBLIC_DIR / 'data'

import sqlite3
db_path = Config.DATA_DIR / 'whovoted.db'
conn = sqlite3.connect(str(db_path))

# Sample VUIDs from the DB
print("=== VOTER REGISTRY DB VUIDs ===")
db_vuids = set()
db_vuid_lengths = Counter()
rows = conn.execute("SELECT vuid FROM voters LIMIT 500000").fetchall()
for r in rows:
    v = r[0]
    db_vuids.add(v)
    db_vuid_lengths[len(v)] += 1

print(f"Total VUIDs in DB: {len(db_vuids):,}")
print(f"VUID length distribution: {dict(db_vuid_lengths)}")
sample_db = list(db_vuids)[:10]
print(f"Sample DB VUIDs: {sample_db}")

# Sample VUIDs from map_data files
print("\n=== MAP_DATA FILE VUIDs ===")
map_vuids = set()
map_vuid_lengths = Counter()
map_vuid_sources = {}  # store a few samples per length

for f in sorted(data_dir.glob('map_data_*.json'))[:3]:  # just check first 3 files
    try:
        with open(f, 'r') as fh:
            geojson = json.load(fh)
        for feature in geojson.get('features', []):
            props = feature.get('properties', {})
            vuid = str(props.get('vuid', '')).strip()
            if not vuid or vuid == 'nan':
                continue
            map_vuids.add(vuid)
            vlen = len(vuid)
            map_vuid_lengths[vlen] += 1
            if vlen not in map_vuid_sources or len(map_vuid_sources[vlen]) < 5:
                map_vuid_sources.setdefault(vlen, []).append(vuid)
        print(f"  {f.name}: loaded")
    except Exception as e:
        print(f"  {f.name}: ERROR {e}")

print(f"Total unique VUIDs from map_data (3 files): {len(map_vuids):,}")
print(f"VUID length distribution: {dict(map_vuid_lengths)}")
for vlen, samples in sorted(map_vuid_sources.items()):
    print(f"  Length {vlen} samples: {samples[:5]}")

# Check overlap
matched = map_vuids & db_vuids
unmatched_map = map_vuids - db_vuids
print(f"\nMatched: {len(matched):,}")
print(f"In map_data but NOT in DB: {len(unmatched_map):,}")

# Try to understand the mismatch — check if zero-padding fixes it
if unmatched_map:
    fixed_by_padding = 0
    fixed_by_stripping = 0
    still_unmatched = 0
    sample_unmatched = []
    
    for v in list(unmatched_map)[:5000]:
        # Try zero-padding to 10
        padded = v.zfill(10)
        # Try stripping leading zeros
        stripped = v.lstrip('0') or '0'
        
        if padded in db_vuids:
            fixed_by_padding += 1
        elif stripped in db_vuids:
            fixed_by_stripping += 1
        elif v.zfill(10) != v and v.zfill(10) in db_vuids:
            fixed_by_padding += 1
        else:
            still_unmatched += 1
            if len(sample_unmatched) < 20:
                sample_unmatched.append(v)
    
    checked = min(5000, len(unmatched_map))
    print(f"\nMismatch analysis (checked {checked:,} unmatched VUIDs):")
    print(f"  Fixed by zero-padding to 10: {fixed_by_padding:,}")
    print(f"  Fixed by stripping leading zeros: {fixed_by_stripping:,}")
    print(f"  Still unmatched: {still_unmatched:,}")
    print(f"\n  Sample unmatched map_data VUIDs:")
    for v in sample_unmatched[:20]:
        padded = v.zfill(10)
        print(f"    '{v}' (len={len(v)}) -> padded='{padded}' in DB? {padded in db_vuids}")

conn.close()
