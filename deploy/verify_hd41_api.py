#!/usr/bin/env python3
"""Simulate what the browser does for HD-41 and check the API response."""
import json
import requests
import sqlite3

# Load districts
with open('/opt/whovoted/public/data/districts.json') as f:
    districts = json.load(f)
hd41 = [f for f in districts['features'] if f['properties']['district_id'] == 'HD-41'][0]

# Load ONLY the cumulative files (what the browser loads)
cum_files = [
    '/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_democratic_cumulative_ev.json',
    '/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_republican_cumulative_ev.json',
]
all_features = []
for mf in cum_files:
    with open(mf) as f:
        data = json.load(f)
    print(f"{mf.split('/')[-1]}: {len(data.get('features', []))} features")
    all_features.extend(data.get('features', []))
print(f"Total features (both parties): {len(all_features)}")

# Deduplicate by VUID (browser's data.js does this)
seen = set()
unique_features = []
for f in all_features:
    vuid = f.get('properties', {}).get('vuid', '')
    if vuid and vuid not in seen:
        seen.add(vuid)
        unique_features.append(f)
print(f"After VUID dedup: {len(unique_features)}")

# Point-in-polygon
def pip(x, y, poly):
    inside = False
    n = len(poly)
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def in_feat(lng, lat, feat):
    g = feat['geometry']
    if g['type'] == 'Polygon':
        return pip(lng, lat, g['coordinates'][0])
    elif g['type'] == 'MultiPolygon':
        return any(pip(lng, lat, p[0]) for p in g['coordinates'])
    return False

# Filter to HD-41 using ALL features (not deduped - matching browser behavior)
print("\nFiltering ALL features (no dedup, matching browser)...")
in_district_all = []
for f in all_features:
    if not f.get('geometry') or not f['geometry'].get('coordinates'):
        continue
    lng, lat = f['geometry']['coordinates']
    if lat == 0 and lng == 0:
        continue
    if in_feat(lng, lat, hd41):
        in_district_all.append(f)
print(f"Features in HD-41 (all, with dupes): {len(in_district_all)}")

# Get VUIDs the way the browser does (may have dupes)
vuids_all = [f['properties'].get('vuid', '') for f in in_district_all if f['properties'].get('vuid')]
vuids_all = [v for v in vuids_all if v]
print(f"VUIDs (with possible dupes): {len(vuids_all)}")
vuids_unique = list(set(vuids_all))
print(f"VUIDs (unique): {len(vuids_unique)}")

# Call the API with the unique VUIDs
print("\nCalling /api/district-stats with unique VUIDs...")
resp = requests.post('http://localhost:5000/api/district-stats',
    json={'vuids': vuids_unique, 'district_id': 'HD-41', 'election_date': '2026-03-03'},
    timeout=120)
data = resp.json()
print(f"API response:")
print(f"  total: {data['total']}")
print(f"  dem: {data['dem']}, rep: {data['rep']}")
print(f"  new_total: {data['new_total']}")
print(f"  r2d: {data['r2d']}, d2r: {data['d2r']}")

# Now call with ALL vuids (including dupes) - this is what browser sends
print("\nCalling /api/district-stats with ALL VUIDs (dupes)...")
resp2 = requests.post('http://localhost:5000/api/district-stats',
    json={'vuids': vuids_all, 'district_id': 'HD-41', 'election_date': '2026-03-03'},
    timeout=120)
data2 = resp2.json()
print(f"API response (with dupes):")
print(f"  total: {data2['total']}")
print(f"  dem: {data2['dem']}, rep: {data2['rep']}")
print(f"  new_total: {data2['new_total']}")
print(f"  r2d: {data2['r2d']}, d2r: {data2['d2r']}")

# Check: does the browser deduplicate?
print("\n=== KEY QUESTION: Does the browser deduplicate VUIDs? ===")
print("campaigns.js sends: votersInDistrict.map(f => f.properties.vuid)")
print("This does NOT deduplicate. If a voter appears in both DEM and REP files,")
print("their VUID appears twice in the list sent to the API.")
print(f"Dupes in VUID list: {len(vuids_all) - len(vuids_unique)}")
