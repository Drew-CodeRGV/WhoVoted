#!/usr/bin/env python3
"""
Update CPct-2 counts using a manually provided list of correct precincts.

USAGE:
1. Provide the correct list of precincts in CORRECT_PRECINCTS below
2. Run this script to update the cache with correct counts
3. Regenerate the boundary polygon based on these precincts

If you don't have the precinct list, provide the official CPct-2 shapefile.
"""

import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'
COUNTY = 'Hidalgo'
YEAR = 2026

# OPTION 1: Provide the correct list of precincts here
# Example: CORRECT_PRECINCTS = ['001', '002', '003', ...]
CORRECT_PRECINCTS = None  # Set to list of precinct names

# OPTION 2: Use current boundary but note the discrepancy
USE_CURRENT_BOUNDARY = True

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("="*80)
print("CPCT-2 MANUAL UPDATE")
print("="*80)

if CORRECT_PRECINCTS:
    print(f"\nUsing manually provided list of {len(CORRECT_PRECINCTS)} precincts")
    precincts = CORRECT_PRECINCTS
else:
    print("\nNo manual precinct list provided.")
    print("Using current boundary from districts.json")
    print("NOTE: This will show higher numbers than certified results.")
    
    # Load current boundary and map precincts
    from pathlib import Path
    import sys
    sys.path.append(str(Path(__file__).parent))
    
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
    
    with open('/opt/whovoted/public/data/districts.json') as f:
        districts = json.load(f)['features']
    
    cpct2 = next((d for d in districts if d['properties'].get('district_id') == 'CPct-2'), None)
    
    cur.execute("""
        SELECT precinct, AVG(lat) as lat, AVG(lng) as lng
        FROM voters WHERE county = ? AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """, (COUNTY,))
    
    precincts = []
    for row in cur.fetchall():
        if point_in_polygon(row['lng'], row['lat'], cpct2['geometry']):
            precincts.append(row['precinct'])
    
    print(f"Mapped {len(precincts)} precincts to CPct-2")

# Calculate statistics
placeholders = ','.join('?' * len(precincts))

# Total registered voters
cur.execute(f"""
    SELECT COUNT(DISTINCT vuid)
    FROM voters
    WHERE county = ? AND precinct IN ({placeholders})
""", [COUNTY] + precincts)
total_voters = cur.fetchone()[0]

# Voters who voted
cur.execute(f"""
    SELECT COUNT(DISTINCT v.vuid)
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders})
    AND ve.election_date = ?
""", [COUNTY] + precincts + [ELECTION_DATE])
total_voted = cur.fetchone()[0]

# Party breakdown
cur.execute(f"""
    SELECT 
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') THEN ve.vuid END) as dem,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('REP','R','Republican') THEN ve.vuid END) as rep
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders})
    AND ve.election_date = ?
""", [COUNTY] + precincts + [ELECTION_DATE])

row = cur.fetchone()
dem_votes = row['dem']
rep_votes = row['rep']

turnout_pct = (total_voted / total_voters * 100) if total_voters > 0 else 0

print(f"\nStatistics:")
print(f"  Total Registered: {total_voters:,}")
print(f"  Total Voted: {total_voted:,} ({turnout_pct:.1f}%)")
print(f"  DEM: {dem_votes:,}")
print(f"  REP: {rep_votes:,}")

# Update cache
cur.execute("""
    DELETE FROM district_counts_cache
    WHERE district_id = 'CPct-2' AND county = ? AND year = ?
""", (COUNTY, YEAR))

cur.execute("""
    INSERT INTO district_counts_cache (
        district_id, district_type, county, year,
        total_voters, voted, not_voted, turnout_percentage,
        dem_votes, rep_votes, cached_at
    ) VALUES (?, 'commissioner', ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
""", ('CPct-2', COUNTY, YEAR, total_voters, total_voted, 
      total_voters - total_voted, turnout_pct, dem_votes, rep_votes))

conn.commit()
conn.close()

print("\n✓ Cache updated")
print("\nNOTE: If these numbers don't match certified results,")
print("you need to provide the correct precinct list or boundary shapefile.")
