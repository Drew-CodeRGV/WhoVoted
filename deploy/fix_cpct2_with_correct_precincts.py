#!/usr/bin/env python3
"""
Fix CPct-2 counts using a corrected precinct list.

Since we can't find the exact boundary that matches certified numbers,
this script allows manual specification of the correct precincts.

The issue: Current boundary has 422 precincts giving 16,321 early votes.
Certified numbers show 9,876 early votes (60% of current).
This means the boundary includes ~167 extra precincts.
"""

import sqlite3
import json
from shapely.geometry import shape, Point, MultiPoint
from shapely.ops import unary_union

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'
ELECTION_DATE = '2026-03-03'
COUNTY = 'Hidalgo'
YEAR = 2026

TARGET_EARLY = 9876
TARGET_EDAY = 3754

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("="*80)
print("CPCT-2 FIX - USING GEOGRAPHIC CONSTRAINTS")
print("="*80)

# CPct-2 is described as "southern Hidalgo County including Hidalgo, McAllen, Pharr, San Juan"
# Let's filter to precincts in or near those cities

# Get all precincts with their locations
cur.execute("""
    SELECT precinct, AVG(lat) as lat, AVG(lng) as lng, COUNT(*) as voters
    FROM voters
    WHERE county = ? AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""", (COUNTY,))

all_hidalgo_precincts = {}
for row in cur.fetchall():
    all_hidalgo_precincts[row['precinct']] = {
        'lat': row['lat'],
        'lng': row['lng'],
        'voters': row['voters']
    }

# McAllen is around 26.20°N, 98.23°W
# Pharr is around 26.19°N, 98.18°W
# San Juan is around 26.19°N, 98.15°W
# Hidalgo is around 26.10°N, 98.26°W

# Southern Hidalgo County would be roughly south of 26.20°N
# and between -98.30°W and -98.10°W

SOUTH_BOUNDARY = 26.20  # North of this is not CPct-2
WEST_BOUNDARY = -98.30
EAST_BOUNDARY = -98.10

filtered_precincts = []
for precinct, data in all_hidalgo_precincts.items():
    lat = data['lat']
    lng = data['lng']
    
    # Southern Hidalgo County filter
    if lat < SOUTH_BOUNDARY and WEST_BOUNDARY < lng < EAST_BOUNDARY:
        filtered_precincts.append(precinct)

print(f"\nFiltered to {len(filtered_precincts)} precincts in southern Hidalgo County")
print(f"(lat < {SOUTH_BOUNDARY}, {WEST_BOUNDARY} < lng < {EAST_BOUNDARY})")

# Get vote counts for these precincts
placeholders = ','.join('?' * len(filtered_precincts))
cur.execute(f"""
    SELECT 
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'early-voting' THEN ve.vuid END) as dem_early,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'election-day' THEN ve.vuid END) as dem_eday,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('REP','R','Republican') THEN ve.vuid END) as rep_total,
        COUNT(DISTINCT ve.vuid) as total_voted
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders})
    AND ve.election_date = ?
    AND ve.data_source = 'county-upload'
""", [COUNTY] + filtered_precincts + [ELECTION_DATE])

row = cur.fetchone()
print(f"\nVote counts:")
print(f"  DEM Early: {row['dem_early']:,} (target: {TARGET_EARLY:,}, diff: {abs(row['dem_early']-TARGET_EARLY)})")
print(f"  DEM EDay: {row['dem_eday']:,} (target: {TARGET_EDAY:,}, diff: {abs(row['dem_eday']-TARGET_EDAY)})")
print(f"  REP Total: {row['rep_total']:,}")
print(f"  Total Voted: {row['total_voted']:,}")

# Try adjusting the boundary
print("\n" + "="*80)
print("TRYING DIFFERENT BOUNDARIES")
print("="*80)

for south_lat in [26.18, 26.19, 26.20, 26.21, 26.22]:
    filtered = [p for p, d in all_hidalgo_precincts.items() 
                if d['lat'] < south_lat and WEST_BOUNDARY < d['lng'] < EAST_BOUNDARY]
    
    if not filtered:
        continue
    
    placeholders = ','.join('?' * len(filtered))
    cur.execute(f"""
        SELECT 
            COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'early-voting' THEN ve.vuid END) as dem_early,
            COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'election-day' THEN ve.vuid END) as dem_eday
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.county = ? AND v.precinct IN ({placeholders})
        AND ve.election_date = ? AND ve.data_source = 'county-upload'
    """, [COUNTY] + filtered + [ELECTION_DATE])
    
    row = cur.fetchone()
    diff = abs(row['dem_early'] - TARGET_EARLY) + abs(row['dem_eday'] - TARGET_EDAY)
    
    print(f"Lat < {south_lat}: {len(filtered)} precincts, Early={row['dem_early']:,}, EDay={row['dem_eday']:,}, Diff={diff}")

conn.close()

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print("Unable to find exact boundary match using geographic filters.")
print("The certified numbers may be:")
print("1. From a different data source or election")
print("2. Using a boundary we don't have access to")
print("3. Calculated using different methodology")
print()
print("RECOMMENDATION: Use the current precinct-based methodology")
print("and note the discrepancy in the report.")
