#!/usr/bin/env python3
"""Regenerate DEM cumulative GeoJSON with correct flip detection.

Now that stale 2026-02-25 records are deleted, the previous election
for DEM 2026-03-03 voters will correctly be 2024-03-05 (or earlier).
"""
import json
import sqlite3
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
DEM_CUM_PATH = '/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_democratic_cumulative_ev.json'
DEM_CUM_DATA_PATH = '/opt/whovoted/data/map_data_Hidalgo_2026_primary_democratic_cumulative_ev.json'
DEM_META_PATH = '/opt/whovoted/public/data/metadata_Hidalgo_2026_primary_democratic_cumulative_ev.json'
DEM_META_DATA_PATH = '/opt/whovoted/data/metadata_Hidalgo_2026_primary_democratic_cumulative_ev.json'

conn = sqlite3.connect(DB_PATH)

# Load current GeoJSON
with open(DEM_CUM_PATH) as f:
    geojson = json.load(f)

print(f"Loaded {len(geojson['features'])} features")

# Build prev_party_map for all DEM 2026 voters
vuids = [f['properties']['vuid'] for f in geojson['features'] if f['properties'].get('vuid')]
print(f"Looking up previous party for {len(vuids)} VUIDs...")

prev_party_map = {}
for i in range(0, len(vuids), 999):
    chunk = vuids[i:i+999]
    ph = ','.join('?' * len(chunk))
    rows = conn.execute(f"""
        SELECT ve.vuid, ve.party_voted
        FROM voter_elections ve
        WHERE ve.vuid IN ({ph})
          AND ve.election_date = (
              SELECT MAX(ve2.election_date) FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid
                AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
          )
          AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
    """, chunk).fetchall()
    for r in rows:
        prev_party_map[r[0]] = r[1]

print(f"Found previous party for {len(prev_party_map)} voters")

# Count flips
r_to_d = 0
d_to_r = 0  # shouldn't happen in DEM file but just in case
updated = 0

for feat in geojson['features']:
    p = feat['properties']
    vuid = p.get('vuid', '')
    if not vuid:
        continue
    
    prev_party = prev_party_map.get(vuid, '')
    current_party = 'Democratic'
    
    if prev_party and prev_party.lower() != current_party.lower():
        p['has_switched_parties'] = True
        p['party_affiliation_previous'] = prev_party
        updated += 1
        if 'republican' in prev_party.lower():
            r_to_d += 1
        else:
            d_to_r += 1
    else:
        # Clear any stale flip data
        if p.get('has_switched_parties'):
            p['has_switched_parties'] = False
            p['party_affiliation_previous'] = ''

print(f"\nFlip results:")
print(f"  R->D: {r_to_d}")
print(f"  Other->D: {d_to_r}")
print(f"  Total updated: {updated}")

# Save updated GeoJSON to both locations
for path in [DEM_CUM_PATH, DEM_CUM_DATA_PATH]:
    with open(path, 'w') as f:
        json.dump(geojson, f)
    print(f"Saved: {path}")

# Also update the day snapshot in data/
import glob
for snap_path in glob.glob('/opt/whovoted/data/map_data_Hidalgo_2026_primary_democratic_*_ev.json'):
    if 'cumulative' in snap_path:
        continue
    with open(snap_path) as f:
        snap_data = json.load(f)
    
    snap_updated = 0
    for feat in snap_data['features']:
        p = feat['properties']
        vuid = p.get('vuid', '')
        prev_party = prev_party_map.get(vuid, '')
        current_party = 'Democratic'
        
        if prev_party and prev_party.lower() != current_party.lower():
            p['has_switched_parties'] = True
            p['party_affiliation_previous'] = prev_party
            snap_updated += 1
        else:
            if p.get('has_switched_parties'):
                p['has_switched_parties'] = False
                p['party_affiliation_previous'] = ''
    
    with open(snap_path, 'w') as f:
        json.dump(snap_data, f)
    print(f"Updated day snapshot: {snap_path} ({snap_updated} flips)")

print("\nDone!")
