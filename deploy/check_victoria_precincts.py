#!/usr/bin/env python3
"""
Check Victoria County precinct matching
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("VICTORIA COUNTY ANALYSIS")
print("=" * 80)

# Victoria voters
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Victoria'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
""", (ELECTION_DATE,))

total_dem = cursor.fetchone()[0]

cursor.execute("""
    SELECT 
        ve.congressional_district,
        COUNT(DISTINCT ve.vuid) as voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Victoria'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.congressional_district
""", (ELECTION_DATE,))

print(f"\nVictoria Democratic voters by district:")
print(f"{'District':<15} {'Voters':>10}")
print("-" * 27)

for row in cursor.fetchall():
    district = row['congressional_district'] or 'UNASSIGNED'
    print(f"{district:<15} {row['voters']:>10,}")

# Sample Victoria precincts
print(f"\nSample Victoria precincts (voting records):")
cursor.execute("""
    SELECT DISTINCT ve.precinct, COUNT(*) as count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Victoria'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.precinct
    ORDER BY count DESC
    LIMIT 20
""", (ELECTION_DATE,))

print(f"{'Precinct':<20} {'Voters':>10}")
print("-" * 32)

for row in cursor.fetchall():
    print(f"{row['precinct']:<20} {row['count']:>10,}")

# Check reference data
print(f"\nVictoria precincts in reference data:")
cursor.execute("""
    SELECT DISTINCT precinct, congressional_district
    FROM precinct_districts
    WHERE county = 'Victoria'
    ORDER BY precinct
    LIMIT 20
""")

print(f"{'Precinct':<20} {'District':>10}")
print("-" * 32)

for row in cursor.fetchall():
    print(f"{row['precinct']:<20} {row['congressional_district']:>10}")

conn.close()
