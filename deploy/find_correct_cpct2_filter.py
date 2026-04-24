#!/usr/bin/env python3
"""
Try different filters to match certified numbers: 9,876 early + 3,754 election day
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

precincts = []
for row in cur.fetchall():
    if point_in_polygon(row['avg_lon'], row['avg_lat'], cpct2['geometry']):
        precincts.append(row['precinct'])

placeholders = ','.join('?' * len(precincts))

print("="*80)
print("TRYING DIFFERENT FILTERS TO MATCH CERTIFIED NUMBERS")
print("="*80)
print(f"Target: {TARGET_EARLY:,} early + {TARGET_EDAY:,} election day")
print()

# Try 1: Only precincts with election day votes
cur.execute(f"""
    SELECT DISTINCT v.precinct
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders})
    AND ve.election_date = '2026-03-03'
    AND ve.voting_method = 'election-day'
    AND ve.data_source = 'county-upload'
""", precincts)

precincts_with_eday = [row['precinct'] for row in cur.fetchall()]
placeholders2 = ','.join('?' * len(precincts_with_eday))

cur.execute(f"""
    SELECT 
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'early-voting' THEN ve.vuid END) as dem_early,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'election-day' THEN ve.vuid END) as dem_eday
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders2})
    AND ve.election_date = '2026-03-03'
    AND ve.data_source = 'county-upload'
""", precincts_with_eday)

row = cur.fetchone()
print(f"Filter 1: Only precincts with election day votes ({len(precincts_with_eday)} precincts)")
print(f"  Early: {row['dem_early']:,}, EDay: {row['dem_eday']:,}")
print(f"  Match: Early={abs(row['dem_early']-TARGET_EARLY)}, EDay={abs(row['dem_eday']-TARGET_EDAY)}")
print()

# Try 2: Maybe it's a different election date?
cur.execute("""
    SELECT 
        ve.election_date,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'early-voting' THEN ve.vuid END) as dem_early,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'election-day' THEN ve.vuid END) as dem_eday
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date >= '2024-01-01'
    GROUP BY ve.election_date
    HAVING dem_early BETWEEN 8000 AND 12000 OR dem_eday BETWEEN 3000 AND 5000
""")

print("Filter 2: Different election dates with similar numbers:")
for row in cur.fetchall():
    print(f"  {row['election_date']}: Early={row['dem_early']:,}, EDay={row['dem_eday']:,}")
    print(f"    Match: Early={abs(row['dem_early']-TARGET_EARLY)}, EDay={abs(row['dem_eday']-TARGET_EDAY)}")
print()

# Try 3: Maybe the ratio is what matters - scale down by a factor
actual_early = 16321
actual_eday = 3874
ratio = TARGET_EARLY / actual_early
print(f"Filter 3: Scaling factor analysis")
print(f"  Ratio: {ratio:.4f}")
print(f"  If we scale: Early={actual_early * ratio:.0f}, EDay={actual_eday * ratio:.0f}")
print(f"  This suggests we have {1/ratio:.2f}x too many precincts")
print()

# Try 4: Check if there's a specific precinct pattern
print("Filter 4: Checking precinct naming patterns")
print(f"  Total precincts: {len(precincts)}")
print(f"  Precincts with 'P ': {len([p for p in precincts if p.startswith('P ')])}")
print(f"  Precincts with 'S ': {len([p for p in precincts if p.startswith('S ')])}")
print(f"  Numeric precincts: {len([p for p in precincts if p[0].isdigit()])}")

conn.close()

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print("The database has ~1.65x more votes than certified.")
print("Possible causes:")
print("1. CPct-2 boundary includes too many precincts")
print("2. Certified numbers are for a different election")
print("3. Certified numbers exclude certain precinct types (P/S precincts?)")
print("4. Data source issue (multiple imports of same data)")
