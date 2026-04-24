#!/usr/bin/env python3
"""
Analyze which precincts are being included in CPct-2 and their vote counts.
Maybe we're including the wrong precincts.
"""

import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'

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
    SELECT precinct, AVG(lat) as avg_lat, AVG(lng) as avg_lon, COUNT(*) as voters
    FROM voters WHERE county = 'Hidalgo' AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""")

precincts_in_cpct2 = []
for row in cur.fetchall():
    if point_in_polygon(row['avg_lon'], row['avg_lat'], cpct2['geometry']):
        precincts_in_cpct2.append(row['precinct'])

print(f"Found {len(precincts_in_cpct2)} precincts in CPct-2")
print(f"\nAll precincts: {', '.join(sorted(precincts_in_cpct2))}")

# Get vote counts by precinct
placeholders = ','.join('?' * len(precincts_in_cpct2))

cur.execute(f"""
    SELECT 
        v.precinct,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'early-voting' THEN ve.vuid END) as dem_early,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'election-day' THEN ve.vuid END) as dem_eday,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('REP','R','Republican') AND ve.voting_method = 'early-voting' THEN ve.vuid END) as rep_early,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('REP','R','Republican') AND ve.voting_method = 'election-day' THEN ve.vuid END) as rep_eday
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders})
    AND ve.election_date = '2026-03-03'
    AND ve.data_source = 'county-upload'
    GROUP BY v.precinct
    ORDER BY dem_early + dem_eday DESC
""", precincts_in_cpct2)

print("\nTop 20 precincts by DEM votes (county-upload only):")
print(f"{'Precinct':<15} {'DEM Early':>10} {'DEM EDay':>10} {'DEM Total':>10} {'REP Total':>10}")
print("-" * 60)

total_dem_early = 0
total_dem_eday = 0
total_rep = 0

for i, row in enumerate(cur.fetchall()):
    if i < 20:
        dem_total = row['dem_early'] + row['dem_eday']
        rep_total = row['rep_early'] + row['rep_eday']
        print(f"{row['precinct']:<15} {row['dem_early']:>10,} {row['dem_eday']:>10,} {dem_total:>10,} {rep_total:>10,}")
    
    total_dem_early += row['dem_early']
    total_dem_eday += row['dem_eday']
    total_rep += row['rep_early'] + row['rep_eday']

print("-" * 60)
print(f"{'TOTAL':<15} {total_dem_early:>10,} {total_dem_eday:>10,} {total_dem_early + total_dem_eday:>10,} {total_rep:>10,}")

print("\n" + "="*80)
print("CERTIFIED vs DATABASE")
print("="*80)
print(f"Certified DEM Early:    9,876")
print(f"Database DEM Early:    {total_dem_early:,}")
print(f"Difference:            {total_dem_early - 9876:,}")
print()
print(f"Certified DEM EDay:     3,754")
print(f"Database DEM EDay:     {total_dem_eday:,}")
print(f"Difference:            {total_dem_eday - 3754:,}")

conn.close()
