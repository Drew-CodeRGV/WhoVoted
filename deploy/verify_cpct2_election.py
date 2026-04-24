#!/usr/bin/env python3
"""
Verify which election we're looking at and check precinct assignments.
"""

import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("="*80)
print("ELECTION VERIFICATION")
print("="*80)

# Check what election_type means
cur.execute("""
    SELECT DISTINCT election_date, election_type, COUNT(DISTINCT vuid) as voters
    FROM voter_elections
    WHERE election_date >= '2024-01-01'
    GROUP BY election_date, election_type
    ORDER BY election_date DESC
""")

print("\nRecent elections:")
for row in cur.fetchall():
    print(f"  {row['election_date']} ({row['election_type']}): {row['voters']:,} voters")

# Check if there's a general election for 2026
cur.execute("""
    SELECT DISTINCT election_date, election_type, COUNT(DISTINCT vuid) as voters
    FROM voter_elections
    WHERE election_date LIKE '2026%'
    GROUP BY election_date, election_type
    ORDER BY election_date
""")

print("\n2026 elections:")
for row in cur.fetchall():
    print(f"  {row['election_date']} ({row['election_type']}): {row['voters']:,} voters")

# Check Hidalgo County specifically
print("\n" + "="*80)
print("HIDALGO COUNTY ELECTIONS")
print("="*80)

cur.execute("""
    SELECT DISTINCT ve.election_date, ve.election_type, COUNT(DISTINCT ve.vuid) as voters
    FROM voter_elections ve
    INNER JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date >= '2024-01-01'
    GROUP BY ve.election_date, ve.election_type
    ORDER BY ve.election_date DESC
""")

for row in cur.fetchall():
    print(f"  {row['election_date']} ({row['election_type']}): {row['voters']:,} voters")

# Check if 2026-03-03 is a primary
print("\n" + "="*80)
print("2026-03-03 ELECTION DETAILS")
print("="*80)

cur.execute("""
    SELECT election_type, COUNT(DISTINCT vuid) as voters
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    GROUP BY election_type
""")

for row in cur.fetchall():
    print(f"  Type: {row['election_type']}, Voters: {row['voters']:,}")

# The user said certified numbers are for "commissioner precinct 2"
# Maybe they mean a different election? Let's check what elections have ~14k DEM votes
print("\n" + "="*80)
print("SEARCHING FOR ELECTIONS WITH ~14K DEM VOTES IN HIDALGO")
print("="*80)

cur.execute("""
    SELECT 
        ve.election_date,
        ve.election_type,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') THEN ve.vuid END) as dem,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('REP','R','Republican') THEN ve.vuid END) as rep,
        COUNT(DISTINCT ve.vuid) as total
    FROM voter_elections ve
    INNER JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date >= '2024-01-01'
    GROUP BY ve.election_date, ve.election_type
    HAVING dem BETWEEN 10000 AND 20000
    ORDER BY ve.election_date DESC
""")

for row in cur.fetchall():
    print(f"  {row['election_date']} ({row['election_type']}): DEM={row['dem']:,}, REP={row['rep']:,}, Total={row['total']:,}")

# Check if the certified numbers might be for a specific data source
print("\n" + "="*80)
print("CHECKING DATA SOURCES FOR CPCT-2")
print("="*80)

# Load CPct-2 boundary
with open(DISTRICTS_FILE) as f:
    districts = json.load(f)['features']

cpct2 = next((d for d in districts if d['properties'].get('district_id') == 'CPct-2'), None)

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

# Check by data source
cur.execute(f"""
    SELECT 
        ve.data_source,
        ve.voting_method,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') THEN ve.vuid END) as dem,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('REP','R','Republican') THEN ve.vuid END) as rep
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders})
    AND ve.election_date = '2026-03-03'
    GROUP BY ve.data_source, ve.voting_method
    ORDER BY ve.data_source, ve.voting_method
""", precincts)

print("\nBy data source and method:")
for row in cur.fetchall():
    print(f"  {row['data_source']} / {row['voting_method']}: DEM={row['dem']:,}, REP={row['rep']:,}")

# Maybe county-upload is the only source we should use?
cur.execute(f"""
    SELECT 
        ve.voting_method,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') THEN ve.vuid END) as dem,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('REP','R','Republican') THEN ve.vuid END) as rep
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders})
    AND ve.election_date = '2026-03-03'
    AND ve.data_source = 'county-upload'
    GROUP BY ve.voting_method
    ORDER BY ve.voting_method
""", precincts)

print("\nCOUNTY-UPLOAD ONLY:")
total_dem = 0
total_rep = 0
for row in cur.fetchall():
    print(f"  {row['voting_method']}: DEM={row['dem']:,}, REP={row['rep']:,}")
    total_dem += row['dem']
    total_rep += row['rep']

print(f"\nTOTAL (county-upload only): DEM={total_dem:,}, REP={total_rep:,}")

conn.close()
