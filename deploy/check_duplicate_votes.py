#!/usr/bin/env python3
"""
Check if there are duplicate vote records causing the discrepancy.
"""

import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'
COUNTY = 'Hidalgo'

with open('/opt/whovoted/deploy/cpct2_correct_precincts.json') as f:
    data = json.load(f)

precincts = data['precincts']

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

placeholders = ','.join('?' * len(precincts))

print("Checking for duplicate vote records...")

# Count with DISTINCT
cur.execute(f"""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders})
    AND ve.election_date = ? AND ve.party_voted = 'Democratic'
    AND ve.voting_method = 'early-voting'
""", [COUNTY] + precincts + [ELECTION_DATE])
distinct_early = cur.fetchone()[0]

# Count without DISTINCT
cur.execute(f"""
    SELECT COUNT(*)
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders})
    AND ve.election_date = ? AND ve.party_voted = 'Democratic'
    AND ve.voting_method = 'early-voting'
""", [COUNTY] + precincts + [ELECTION_DATE])
total_early = cur.fetchone()[0]

print(f"\nEarly voting:")
print(f"  DISTINCT vuids: {distinct_early:,}")
print(f"  Total records: {total_early:,}")
print(f"  Duplicates: {total_early - distinct_early:,}")

# Find voters with multiple early voting records
cur.execute(f"""
    SELECT ve.vuid, v.precinct, COUNT(*) as cnt
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders})
    AND ve.election_date = ? AND ve.party_voted = 'Democratic'
    AND ve.voting_method = 'early-voting'
    GROUP BY ve.vuid, v.precinct
    HAVING COUNT(*) > 1
    LIMIT 10
""", [COUNTY] + precincts + [ELECTION_DATE])

duplicates = cur.fetchall()
if duplicates:
    print(f"\nFound {len(duplicates)} voters with duplicate early voting records:")
    for row in duplicates:
        print(f"  VUID {row['vuid']} in precinct {row['precinct']}: {row['cnt']} records")

conn.close()
