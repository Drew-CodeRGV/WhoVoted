#!/usr/bin/env python3
"""
Debug: why are we only matching 36 of 66 canvass precincts to VTD boundaries?

The canvass has 66 precincts (006, 007, 008, 013, 018, ...).
The VTD file has 259 Hidalgo County VTDs (0001-0259).
We should be able to match all 66 canvass precincts to VTDs.

Let's see what's not matching.
"""
import json, sqlite3

VTD_PATH = '/opt/whovoted/public/data/hidalgo_vtd_boundaries.json'
DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
DB_PATH = '/opt/whovoted/data/whovoted.db'

# Load VTD boundaries
with open(VTD_PATH) as f:
    vtd_data = json.load(f)
vtd_ids = set()
for feat in vtd_data['features']:
    vtd_id = feat['properties'].get('vtd_id', feat['properties'].get('VTD', ''))
    vtd_ids.add(vtd_id)
    vtd_ids.add(vtd_id.lstrip('0') or '0')

print(f"VTD file: {len(vtd_data['features'])} features")
print(f"VTD IDs (sample): {sorted(list(vtd_ids))[:20]}")

# Load canvass precincts (from the DB)
conn = sqlite3.connect(DB_PATH)
canvass_pcts = set(r[0] for r in conn.execute(
    "SELECT DISTINCT precinct FROM hd41_candidate_results WHERE election_date='2026-03-03'"
).fetchall())
print(f"\nCanvass precincts: {len(canvass_pcts)}")
print(f"Canvass IDs: {sorted(canvass_pcts)}")

# Check which canvass precincts match VTDs
matched = []
unmatched = []
for pct in sorted(canvass_pcts):
    # Try various normalizations
    norm = pct.lstrip('0') or '0'
    padded = pct.zfill(4)
    if pct in vtd_ids or norm in vtd_ids or padded in vtd_ids:
        matched.append(pct)
    else:
        unmatched.append(pct)

print(f"\nMatched to VTD: {len(matched)}")
print(f"Unmatched: {len(unmatched)}")
if unmatched:
    print(f"  Unmatched IDs: {unmatched}")

# Now check: which VTDs are inside HD-41?
with open(DISTRICTS_PATH) as f:
    districts = json.load(f)
hd41 = next(f for f in districts['features'] if f['properties'].get('district_id') == 'HD-41')
hd41_geom = hd41['geometry']

def point_in_polygon(x, y, ring):
    n = len(ring); inside = False; j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]; xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def point_in_geom(lng, lat, geom):
    if geom['type'] == 'Polygon': return point_in_polygon(lng, lat, geom['coordinates'][0])
    elif geom['type'] == 'MultiPolygon': return any(point_in_polygon(lng, lat, p[0]) for p in geom['coordinates'])
    return False

# For each canvass precinct, find its VTD and check if centroid is inside HD-41
print("\nChecking which canvass precincts have VTDs inside HD-41:")
inside_count = 0
outside_count = 0
for feat in vtd_data['features']:
    vtd_id = feat['properties'].get('vtd_id', '')
    norm = vtd_id.lstrip('0') or '0'
    # Is this a canvass precinct?
    if vtd_id not in canvass_pcts and norm not in canvass_pcts and vtd_id.zfill(3) not in canvass_pcts:
        continue
    # Get centroid
    geom = feat['geometry']
    coords = geom['coordinates'][0] if geom['type'] == 'Polygon' else geom['coordinates'][0][0]
    cx = sum(c[0] for c in coords) / len(coords)
    cy = sum(c[1] for c in coords) / len(coords)
    inside = point_in_geom(cx, cy, hd41_geom)
    if inside:
        inside_count += 1
    else:
        outside_count += 1
        # Find which canvass ID this matches
        match_id = vtd_id if vtd_id in canvass_pcts else (norm if norm in canvass_pcts else vtd_id.zfill(3))
        print(f"  OUTSIDE: VTD {vtd_id} (canvass pct {match_id}) — centroid ({cy:.4f}, {cx:.4f})")

print(f"\n  Inside HD-41: {inside_count}")
print(f"  Outside HD-41: {outside_count}")
print(f"\n  The {outside_count} 'outside' precincts are being excluded by geometric verification.")
print(f"  This may be because the TLC boundary (PLANH2316) doesn't perfectly align with")
print(f"  the VTD boundaries, or the centroid falls just outside the polygon edge.")

conn.close()
