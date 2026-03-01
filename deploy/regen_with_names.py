#!/usr/bin/env python3
"""Regenerate cumulative EV GeoJSON files with voter names/precinct from DB.

The existing cumulative files have empty name/firstname/lastname/precinct
because the resolver wasn't selecting those columns. This script patches
the existing GeoJSON in-place by looking up each VUID in the voters table.
"""
import json
import sqlite3
import shutil
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = Path('/opt/whovoted/data')
PUBLIC_DIR = Path('/opt/whovoted/public/data')

conn = sqlite3.connect(DB_PATH)

# Build VUID -> (firstname, lastname, precinct) lookup
print("Building voter name lookup from DB...")
rows = conn.execute("SELECT vuid, firstname, lastname, precinct FROM voters").fetchall()
name_lookup = {}
for vuid, fn, ln, pct in rows:
    name_lookup[vuid] = {
        'firstname': fn or '',
        'lastname': ln or '',
        'precinct': pct or '',
    }
print(f"  Loaded {len(name_lookup):,} voters")

# Count how many have names
has_name = sum(1 for v in name_lookup.values() if v['firstname'] or v['lastname'])
print(f"  {has_name:,} have names, {len(name_lookup) - has_name:,} missing names")

for party in ['democratic', 'republican']:
    cum_file = DATA_DIR / f'map_data_Hidalgo_2026_primary_{party}_cumulative_ev.json'
    if not cum_file.exists():
        print(f"  SKIP {party} — file not found")
        continue
    
    print(f"\nPatching {party}...")
    with open(cum_file) as f:
        data = json.load(f)
    
    features = data.get('features', [])
    patched = 0
    still_empty = 0
    
    for feat in features:
        props = feat.get('properties', {})
        vuid = props.get('vuid', '')
        if not vuid:
            continue
        
        info = name_lookup.get(vuid, {})
        fn = info.get('firstname', '')
        ln = info.get('lastname', '')
        pct = info.get('precinct', '')
        
        if fn or ln:
            props['firstname'] = fn
            props['lastname'] = ln
            props['name'] = f"{fn} {ln}".strip()
            patched += 1
        else:
            still_empty += 1
        
        if pct:
            props['precinct'] = pct
    
    print(f"  {patched:,} patched, {still_empty:,} still missing names")
    
    # Write back
    with open(cum_file, 'w') as f:
        json.dump(data, f)
    print(f"  Saved {cum_file.name}")
    
    # Copy to public dir
    pub_dest = PUBLIC_DIR / cum_file.name
    shutil.copy2(cum_file, pub_dest)
    print(f"  Deployed to {pub_dest}")

# Also patch day snapshots so future cumulative rebuilds keep names
print("\nPatching day snapshots...")
for party in ['democratic', 'republican']:
    pattern = f'map_data_Hidalgo_2026_primary_{party}_*_ev.json'
    for snap_file in sorted(DATA_DIR.glob(pattern)):
        if 'cumulative' in snap_file.name:
            continue
        with open(snap_file) as f:
            snap_data = json.load(f)
        
        snap_patched = 0
        for feat in snap_data.get('features', []):
            props = feat.get('properties', {})
            vuid = props.get('vuid', '')
            if not vuid:
                continue
            info = name_lookup.get(vuid, {})
            fn = info.get('firstname', '')
            ln = info.get('lastname', '')
            pct = info.get('precinct', '')
            if fn or ln:
                props['firstname'] = fn
                props['lastname'] = ln
                props['name'] = f"{fn} {ln}".strip()
                snap_patched += 1
            if pct:
                props['precinct'] = pct
        
        with open(snap_file, 'w') as f:
            json.dump(snap_data, f)
        print(f"  {snap_file.name}: {snap_patched:,} patched")

conn.close()
print("\nDone!")
