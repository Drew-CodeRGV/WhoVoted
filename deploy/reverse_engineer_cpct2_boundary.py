#!/usr/bin/env python3
"""
Reverse engineer the correct CPct-2 boundary by finding which subset of precincts
gives us the certified vote totals: 9,876 early + 3,754 election day DEM votes.

Strategy:
1. Get all precincts currently in CPct-2 with their vote counts
2. Try to find a subset that matches the certified totals
3. Use geographic clustering to identify the correct boundary
"""

import sqlite3
import json
from collections import defaultdict

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'

TARGET_EARLY = 9876
TARGET_EDAY = 3754
TOLERANCE = 50  # Allow 50 vote difference

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

print("="*80)
print("REVERSE ENGINEERING CPCT-2 BOUNDARY")
print("="*80)

# Load current CPct-2 boundary
with open(DISTRICTS_FILE) as f:
    districts = json.load(f)['features']

cpct2 = next((d for d in districts if d['properties'].get('district_id') == 'CPct-2'), None)

# Get all precincts with their centroids
cur.execute("""
    SELECT precinct, AVG(lat) as avg_lat, AVG(lng) as avg_lon, COUNT(*) as voters
    FROM voters WHERE county = 'Hidalgo' AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""")

all_precincts = {}
current_cpct2_precincts = []

for row in cur.fetchall():
    precinct = row['precinct']
    lat = row['avg_lat']
    lng = row['avg_lon']
    all_precincts[precinct] = {'lat': lat, 'lng': lng, 'voters': row['voters']}
    
    if point_in_polygon(lng, lat, cpct2['geometry']):
        current_cpct2_precincts.append(precinct)

print(f"\nCurrent boundary includes {len(current_cpct2_precincts)} precincts")

# Get vote counts for each precinct
placeholders = ','.join('?' * len(current_cpct2_precincts))
cur.execute(f"""
    SELECT 
        v.precinct,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'early-voting' THEN ve.vuid END) as dem_early,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'election-day' THEN ve.vuid END) as dem_eday,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('REP','R','Republican') THEN ve.vuid END) as rep_total
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders})
    AND ve.election_date = '2026-03-03'
    AND ve.data_source = 'county-upload'
    GROUP BY v.precinct
""", current_cpct2_precincts)

precinct_votes = {}
for row in cur.fetchall():
    precinct_votes[row['precinct']] = {
        'dem_early': row['dem_early'],
        'dem_eday': row['dem_eday'],
        'rep_total': row['rep_total']
    }

# Strategy: The certified numbers suggest we need ~60% of current precincts
# CPct-2 is described as "southern Hidalgo County including Hidalgo, McAllen, Pharr, San Juan"
# Let's filter to precincts in those cities or south of a certain latitude

print("\n" + "="*80)
print("GEOGRAPHIC ANALYSIS")
print("="*80)

# Calculate latitude distribution
lats = [all_precincts[p]['lat'] for p in current_cpct2_precincts]
lats.sort()
median_lat = lats[len(lats)//2]
q1_lat = lats[len(lats)//4]
q3_lat = lats[3*len(lats)//4]

print(f"Latitude range: {min(lats):.4f} to {max(lats):.4f}")
print(f"Q1: {q1_lat:.4f}, Median: {median_lat:.4f}, Q3: {q3_lat:.4f}")

# Try filtering to southern 60% (below Q2)
southern_precincts = [p for p in current_cpct2_precincts if all_precincts[p]['lat'] < median_lat]
print(f"\nSouthern half: {len(southern_precincts)} precincts")

early_sum = sum(precinct_votes.get(p, {}).get('dem_early', 0) for p in southern_precincts)
eday_sum = sum(precinct_votes.get(p, {}).get('dem_eday', 0) for p in southern_precincts)
print(f"  DEM Early: {early_sum:,}, EDay: {eday_sum:,}")
print(f"  Match: Early diff={abs(early_sum-TARGET_EARLY)}, EDay diff={abs(eday_sum-TARGET_EDAY)}")

conn.close()

print("\n" + "="*80)
print("NEXT STEP")
print("="*80)
print("Need to identify which specific precincts to include.")
print("Options:")
print("1. Filter by latitude threshold")
print("2. Filter by city boundaries")
print("3. Use election results to work backwards")
