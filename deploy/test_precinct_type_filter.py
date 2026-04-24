#!/usr/bin/env python3
"""
Test if excluding certain precinct types (P, S) gets us to the certified numbers.
"""

import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'

TARGET_EARLY = 9876
TARGET_EDAY = 3754

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def point_in_polygon(lng, lat, geometry):
    gtype = geometry.get('type', '')
    coords = geometry.get('coordinates', [])
    if gtype == 'Polygon':
        return _point_in_ring(lng, lat, coords[0])
    elif gtype == 'MultiPolygon':
        return any(_point_in_ring(lng, lat, poly[0]) for poly in coords)
    return False

def _point_in_ring(lng, lat, ring):
    inside = False
    n = len(ring)
    p1_lng, p1_lat = ring[0]
    for i in range(1, n + 1):
        p2_lng, p2_lat = ring[i % n]
        if lat > min(p1_lat, p2_lat):
            if lat <= max(p1_lat, p2_lat):
                if lng <= max(p1_lng, p2_lng):
                    if p1_lat != p2_lat:
                        x_inters = (lat - p1_lat) * (p2_lng - p1_lng) / (p2_lat - p1_lat) + p1_lng
                    if p1_lng == p2_lng or lng <= x_inters:
                        inside = not inside
        p1_lng, p1_lat = p2_lng, p2_lat
    return inside

with open(DISTRICTS_FILE) as f:
    districts = json.load(f)['features']

cpct2 = next((d for d in districts if d['properties'].get('district_id') == 'CPct-2'), None)

cur.execute("""
    SELECT precinct, AVG(lat) as avg_lat, AVG(lng) as avg_lon
    FROM voters WHERE county = 'Hidalgo' AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""")

all_precincts = []
for row in cur.fetchall():
    if point_in_polygon(row['avg_lon'], row['avg_lat'], cpct2['geometry']):
        all_precincts.append(row['precinct'])

print("="*80)
print("TESTING PRECINCT TYPE FILTERS")
print("="*80)
print(f"Total precincts in current boundary: {len(all_precincts)}")

# Categorize precincts
p_precincts = [p for p in all_precincts if p.startswith('P ')]
s_precincts = [p for p in all_precincts if p.startswith('S ')]
numeric_precincts = [p for p in all_precincts if not p.startswith('P ') and not p.startswith('S ')]

print(f"  P precincts: {len(p_precincts)}")
print(f"  S precincts: {len(s_precincts)}")
print(f"  Numeric precincts: {len(numeric_precincts)}")

# Test different filters
filters = [
    ("All precincts", all_precincts),
    ("Exclude P precincts", [p for p in all_precincts if not p.startswith('P ')]),
    ("Exclude S precincts", [p for p in all_precincts if not p.startswith('S ')]),
    ("Exclude P and S", numeric_precincts),
    ("Only P precincts", p_precincts),
    ("Only S precincts", s_precincts),
]

for filter_name, precincts in filters:
    if not precincts:
        continue
    
    placeholders = ','.join('?' * len(precincts))
    cur.execute(f"""
        SELECT 
            COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'early-voting' THEN ve.vuid END) as dem_early,
            COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'election-day' THEN ve.vuid END) as dem_eday
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders})
        AND ve.election_date = '2026-03-03'
        AND ve.data_source = 'county-upload'
    """, precincts)
    
    row = cur.fetchone()
    early_diff = abs(row['dem_early'] - TARGET_EARLY)
    eday_diff = abs(row['dem_eday'] - TARGET_EDAY)
    total_diff = early_diff + eday_diff
    
    print(f"\n{filter_name} ({len(precincts)} precincts):")
    print(f"  Early: {row['dem_early']:,} (diff: {early_diff})")
    print(f"  EDay: {row['dem_eday']:,} (diff: {eday_diff})")
    print(f"  Total diff: {total_diff}")
    
    if total_diff < 200:
        print("  ✓ MATCH FOUND!")

conn.close()
