#!/usr/bin/env python3
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
    SELECT precinct, AVG(lat) as avg_lat, AVG(lng) as avg_lon
    FROM voters WHERE county = 'Hidalgo' AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""")

precincts = [row['precinct'] for row in cur.fetchall() 
             if point_in_polygon(row['avg_lon'], row['avg_lat'], cpct2['geometry'])]

placeholders = ','.join('?' * len(precincts))

# Count distinct VUIDs by voting method and party
cur.execute(f"""
    SELECT ve.voting_method, ve.party_voted, COUNT(DISTINCT ve.vuid) as unique_voters
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
    GROUP BY ve.voting_method, ve.party_voted
    ORDER BY ve.voting_method, ve.party_voted
""", precincts + [ELECTION_DATE])

print("DISTINCT voters by method and party:")
for row in cur.fetchall():
    print(f"  {row[0]} - {row[1]}: {row[2]}")

# Check for voters with multiple records
cur.execute(f"""
    SELECT ve.vuid, ve.voting_method, ve.party_voted, COUNT(*) as cnt
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
    GROUP BY ve.vuid, ve.voting_method, ve.party_voted
    HAVING cnt > 1
    LIMIT 20
""", precincts + [ELECTION_DATE])

dupes = cur.fetchall()
if dupes:
    print(f"\nVoters with duplicate records (same method/party): {len(dupes)}")
    for row in dupes[:10]:
        print(f"  {row[0]}: {row[1]} {row[2]} x{row[3]}")
