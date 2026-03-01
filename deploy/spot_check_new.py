#!/usr/bin/env python3
"""Spot-check 20 'new voters' in HD-41 to confirm they have no prior records."""
import sqlite3
import json

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row

# Load HD-41 boundary
with open('/opt/whovoted/public/data/districts.json') as f:
    districts = json.load(f)
hd41 = [f for f in districts['features'] if f['properties']['district_id'] == 'HD-41'][0]

# Load cumulative files
files = [
    '/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_democratic_cumulative_ev.json',
    '/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_republican_cumulative_ev.json',
]
features = []
for mf in files:
    with open(mf) as f:
        features.extend(json.load(f).get('features', []))

def pip(x, y, poly):
    inside = False
    j = len(poly) - 1
    for i in range(len(poly)):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj-xi)*(y-yi)/(yj-yi)+xi):
            inside = not inside
        j = i
    return inside

def in_feat(lng, lat, feat):
    g = feat['geometry']
    if g['type'] == 'Polygon': return pip(lng, lat, g['coordinates'][0])
    return any(pip(lng, lat, p[0]) for p in g['coordinates'])

# Get HD-41 VUIDs
vuids = []
for f in features:
    if not f.get('geometry') or not f['geometry'].get('coordinates'): continue
    lng, lat = f['geometry']['coordinates']
    if lat == 0 and lng == 0: continue
    if in_feat(lng, lat, hd41):
        v = f['properties'].get('vuid', '')
        if v: vuids.append(v)

# Find new voters via DB
new_vuids = []
for v in vuids:
    prior = conn.execute("""
        SELECT COUNT(*) FROM voter_elections 
        WHERE vuid=? AND election_date < '2026-03-03'
        AND party_voted != '' AND party_voted IS NOT NULL
    """, (v,)).fetchone()[0]
    if prior == 0:
        new_vuids.append(v)

print(f"HD-41 voters: {len(vuids)}, New: {len(new_vuids)}")
print(f"\nSpot-checking 20 new voters (full election history):")
for v in new_vuids[:20]:
    recs = conn.execute(
        "SELECT election_date, party_voted, voting_method FROM voter_elections WHERE vuid=? ORDER BY election_date",
        (v,)).fetchall()
    print(f"\n  VUID {v}: {len(recs)} total record(s)")
    for r in recs:
        print(f"    {r['election_date']}: {r['party_voted']} ({r['voting_method']})")

print(f"\nSpot-checking 10 RETURNING voters (should have prior records):")
returning = [v for v in vuids if v not in set(new_vuids)][:10]
for v in returning:
    recs = conn.execute(
        "SELECT election_date, party_voted, voting_method FROM voter_elections WHERE vuid=? ORDER BY election_date",
        (v,)).fetchall()
    print(f"\n  VUID {v}: {len(recs)} total record(s)")
    for r in recs:
        print(f"    {r['election_date']}: {r['party_voted']} ({r['voting_method']})")

conn.close()
