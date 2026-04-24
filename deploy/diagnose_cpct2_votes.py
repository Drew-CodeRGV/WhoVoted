#!/usr/bin/env python3
"""Diagnose CPct-2 vote counting to find discrepancy."""
import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'
ELECTION_DATE = '2026-03-03'

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

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

with open(DISTRICTS_FILE) as f:
    districts = json.load(f)['features']

cpct2 = next((d for d in districts if d['properties'].get('district_id') == 'CPct-2'), None)

cur = conn.cursor()
cur.execute("""
    SELECT precinct, AVG(lat) as avg_lat, AVG(lng) as avg_lon, COUNT(*) as voters
    FROM voters WHERE county = 'Hidalgo' AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""")

precincts = [row['precinct'] for row in cur.fetchall() 
             if point_in_polygon(row['avg_lon'], row['avg_lat'], cpct2['geometry'])]

print(f"CPct-2 has {len(precincts)} precincts")

# Check voter_elections table structure
cur.execute("PRAGMA table_info(voter_elections)")
cols = [row[1] for row in cur.fetchall()]
print(f"\nvoter_elections columns: {cols}")

# Check what party values exist
placeholders = ','.join('?' * len(precincts))
cur.execute(f"""
    SELECT DISTINCT ve.party_voted, COUNT(*) as cnt
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
    GROUP BY ve.party_voted
    ORDER BY cnt DESC
""", precincts + [ELECTION_DATE])

print("\nParty values in voter_elections:")
for row in cur.fetchall():
    print(f"  {row[0]}: {row[1]}")

# Check voting_method breakdown
if 'voting_method' in cols:
    cur.execute(f"""
        SELECT ve.voting_method, 
               SUM(CASE WHEN ve.party_voted IN ('DEM','D','Democratic') THEN 1 ELSE 0 END) as dem,
               SUM(CASE WHEN ve.party_voted IN ('REP','R','Republican') THEN 1 ELSE 0 END) as rep,
               COUNT(*) as total
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
        GROUP BY ve.voting_method
    """, precincts + [ELECTION_DATE])
    
    print("\nBy voting method:")
    for row in cur.fetchall():
        print(f"  {row[0]}: DEM={row[1]}, REP={row[2]}, Total={row[3]}")

# Check for duplicates
cur.execute(f"""
    SELECT ve.vuid, COUNT(*) as cnt
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
    GROUP BY ve.vuid
    HAVING cnt > 1
    LIMIT 10
""", precincts + [ELECTION_DATE])

dupes = cur.fetchall()
if dupes:
    print(f"\nFound {len(dupes)} voters with multiple records")
    for row in dupes[:5]:
        print(f"  VUID {row[0]}: {row[1]} records")
