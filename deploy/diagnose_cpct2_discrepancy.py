#!/usr/bin/env python3
"""
Diagnose why CPct-2 shows 22,851 DEM votes instead of certified 13,999.
Certified numbers: 9,876 early + 3,754 election day = 13,630 DEM (not 13,999?)
"""

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

print("="*80)
print("CPCT-2 VOTE COUNT DIAGNOSTIC")
print("="*80)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Load CPct-2 boundary
with open(DISTRICTS_FILE) as f:
    districts = json.load(f)['features']

cpct2 = next((d for d in districts if d['properties'].get('district_id') == 'CPct-2'), None)
if not cpct2:
    print("ERROR: CPct-2 not found in districts.json")
    exit(1)

# Map precincts to CPct-2
cur = conn.cursor()
cur.execute("""
    SELECT precinct, AVG(lat) as avg_lat, AVG(lng) as avg_lon, COUNT(*) as voters
    FROM voters WHERE county = 'Hidalgo' AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""")

precincts = []
for row in cur.fetchall():
    if point_in_polygon(row['avg_lon'], row['avg_lat'], cpct2['geometry']):
        precincts.append(row['precinct'])

print(f"\nFound {len(precincts)} precincts in CPct-2")
print(f"Sample precincts: {', '.join(sorted(precincts)[:10])}")

placeholders = ','.join('?' * len(precincts))

# Check what elections exist
print("\n" + "="*80)
print("ELECTIONS IN DATABASE")
print("="*80)
cur.execute("""
    SELECT DISTINCT election_date, COUNT(DISTINCT vuid) as voters
    FROM voter_elections
    GROUP BY election_date
    ORDER BY election_date DESC
""")
for row in cur.fetchall():
    print(f"  {row['election_date']}: {row['voters']:,} voters")

# Check election types for our date
print("\n" + "="*80)
print(f"ELECTION TYPES FOR {ELECTION_DATE}")
print("="*80)
cur.execute(f"""
    SELECT ve.election_type, COUNT(DISTINCT ve.vuid) as cnt
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
    GROUP BY ve.election_type
""", precincts + [ELECTION_DATE])
for row in cur.fetchall():
    print(f"  {row['election_type']}: {row['cnt']:,}")

# Check data sources
print("\n" + "="*80)
print("DATA SOURCES")
print("="*80)
cur.execute(f"""
    SELECT ve.data_source, COUNT(DISTINCT ve.vuid) as cnt
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
    GROUP BY ve.data_source
""", precincts + [ELECTION_DATE])
for row in cur.fetchall():
    print(f"  {row['data_source']}: {row['cnt']:,}")

# Check voting methods
print("\n" + "="*80)
print("VOTING METHODS")
print("="*80)
cur.execute(f"""
    SELECT ve.voting_method, COUNT(DISTINCT ve.vuid) as cnt
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
    GROUP BY ve.voting_method
""", precincts + [ELECTION_DATE])
for row in cur.fetchall():
    print(f"  {row['voting_method']}: {row['cnt']:,}")

# Detailed breakdown by method and party
print("\n" + "="*80)
print("DETAILED BREAKDOWN: METHOD x PARTY")
print("="*80)
cur.execute(f"""
    SELECT 
        ve.voting_method,
        ve.party_voted,
        COUNT(DISTINCT ve.vuid) as cnt
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
    GROUP BY ve.voting_method, ve.party_voted
    ORDER BY ve.voting_method, ve.party_voted
""", precincts + [ELECTION_DATE])

method_totals = {}
for row in cur.fetchall():
    method = row['voting_method'] or 'NULL'
    party = row['party_voted'] or 'NULL'
    cnt = row['cnt']
    
    if method not in method_totals:
        method_totals[method] = {'DEM': 0, 'REP': 0, 'OTHER': 0}
    
    party_upper = str(party).upper()
    if party_upper in ('DEM', 'D', 'DEMOCRATIC'):
        method_totals[method]['DEM'] += cnt
        print(f"  {method} / {party}: {cnt:,} (DEM)")
    elif party_upper in ('REP', 'R', 'REPUBLICAN'):
        method_totals[method]['REP'] += cnt
        print(f"  {method} / {party}: {cnt:,} (REP)")
    else:
        method_totals[method]['OTHER'] += cnt
        print(f"  {method} / {party}: {cnt:,} (OTHER)")

print("\n" + "="*80)
print("SUMMARY BY METHOD")
print("="*80)
total_dem = 0
total_rep = 0
for method, counts in method_totals.items():
    print(f"{method}:")
    print(f"  DEM: {counts['DEM']:,}")
    print(f"  REP: {counts['REP']:,}")
    print(f"  OTHER: {counts['OTHER']:,}")
    total_dem += counts['DEM']
    total_rep += counts['REP']

print("\n" + "="*80)
print("GRAND TOTALS")
print("="*80)
print(f"DEM: {total_dem:,}")
print(f"REP: {total_rep:,}")
print(f"TOTAL: {total_dem + total_rep:,}")

print("\n" + "="*80)
print("CERTIFIED NUMBERS (USER PROVIDED)")
print("="*80)
print("DEM Early: 9,876")
print("DEM Election Day: 3,754")
print("DEM Total: 13,630 (or 13,999?)")
print(f"\nDISCREPANCY: {total_dem - 13999:,} extra DEM votes in database")

# Check if there are multiple records per voter
print("\n" + "="*80)
print("CHECKING FOR DUPLICATE RECORDS")
print("="*80)
cur.execute(f"""
    SELECT v.vuid, COUNT(*) as record_count
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders}) AND ve.election_date = ?
    AND ve.party_voted IN ('DEM', 'D', 'Democratic')
    GROUP BY v.vuid
    HAVING COUNT(*) > 1
    LIMIT 10
""", precincts + [ELECTION_DATE])

duplicates = cur.fetchall()
if duplicates:
    print(f"Found {len(duplicates)} voters with multiple records:")
    for row in duplicates:
        print(f"  VUID {row['vuid']}: {row['record_count']} records")
else:
    print("No duplicate records found")

conn.close()
