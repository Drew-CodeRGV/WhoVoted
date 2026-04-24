#!/usr/bin/env python3
"""Regenerate Commissioner Precinct 2 report cache using correct precinct-based methodology."""
import sqlite3
import json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'
CACHE_DIR = '/opt/whovoted/public/cache'
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
if not cpct2:
    print("CPct-2 not found")
    exit(1)

cur = conn.cursor()
cur.execute("""
    SELECT precinct, AVG(lat) as avg_lat, AVG(lng) as avg_lon, COUNT(*) as voters
    FROM voters WHERE county = 'Hidalgo' AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""")

precincts = [row['precinct'] for row in cur.fetchall() 
             if point_in_polygon(row['avg_lon'], row['avg_lat'], cpct2['geometry'])]

placeholders = ','.join('?' * len(precincts))
cur.execute(f"""
    SELECT v.county, COUNT(DISTINCT v.vuid) as total,
           SUM(CASE WHEN ve.party_voted IN ('DEM','D','Democratic') THEN 1 ELSE 0 END) as dem,
           SUM(CASE WHEN ve.party_voted IN ('REP','R','Republican') THEN 1 ELSE 0 END) as rep
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
    GROUP BY v.county
""", precincts + [ELECTION_DATE])

county_breakdown = {row['county']: {'total': row['total'], 'dem': row['dem'], 'rep': row['rep']} 
                    for row in cur.fetchall()}

cur.execute(f"""
    SELECT COUNT(DISTINCT v.vuid) as total,
           SUM(CASE WHEN ve.party_voted IN ('DEM','D','Democratic') THEN 1 ELSE 0 END) as dem,
           SUM(CASE WHEN ve.party_voted IN ('REP','R','Republican') THEN 1 ELSE 0 END) as rep
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
""", precincts + [ELECTION_DATE])

row = cur.fetchone()
report = {
    'district_id': 'CPct-2',
    'district_name': 'Commissioner Precinct 2',
    'total': row['total'],
    'dem': row['dem'],
    'rep': row['rep'],
    'dem_share': round(row['dem'] / (row['dem'] + row['rep']) * 100, 1) if (row['dem'] + row['rep']) else 0,
    'county_breakdown': county_breakdown,
    'generated_at': __import__('time').time()
}

Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
with open(f"{CACHE_DIR}/district_report_Commissioner_Precinct_2.json", 'w') as f:
    json.dump(report, f)

print(f"CPct-2: {report['total']} voted, DEM={report['dem']}, REP={report['rep']}")
print(f"Counties: {list(county_breakdown.keys())}")
