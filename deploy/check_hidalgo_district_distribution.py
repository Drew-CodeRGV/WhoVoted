#!/usr/bin/env python3
"""
Check which districts Hidalgo voters are assigned to
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("HIDALGO DISTRICT DISTRIBUTION")
print("=" * 80)

# Check all districts for Hidalgo voters
cursor.execute("""
    SELECT 
        ve.congressional_district,
        COUNT(DISTINCT ve.vuid) as voters,
        COUNT(CASE WHEN ve.party_voted = 'Democratic' THEN 1 END) as dem,
        COUNT(CASE WHEN ve.party_voted = 'Republican' THEN 1 END) as rep
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    GROUP BY ve.congressional_district
    ORDER BY voters DESC
""", (ELECTION_DATE,))

print(f"\n{'District':<15} {'Total Voters':>15} {'Democratic':>15} {'Republican':>15}")
print("-" * 62)

total_voters = 0
total_dem = 0
total_rep = 0

for row in cursor.fetchall():
    district = row['congressional_district'] or 'UNASSIGNED'
    print(f"{district:<15} {row['voters']:>15,} {row['dem']:>15,} {row['rep']:>15,}")
    total_voters += row['voters']
    total_dem += row['dem']
    total_rep += row['rep']

print("-" * 62)
print(f"{'TOTAL':<15} {total_voters:>15,} {total_dem:>15,} {total_rep:>15,}")

# Check if this matches reality
print("\n" + "=" * 80)
print("REALITY CHECK")
print("=" * 80)

print("\nHidalgo County spans multiple congressional districts:")
print("  - TX-15: Southern Hidalgo (McAllen, Mission, Edinburg area)")
print("  - TX-28: Western Hidalgo")  
print("  - TX-34: Eastern Hidalgo")

print(f"\nOur data shows:")
cursor.execute("""
    SELECT congressional_district, COUNT(DISTINCT ve.vuid) as dem_voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.congressional_district IS NOT NULL
    AND ve.congressional_district != ''
    GROUP BY ve.congressional_district
    ORDER BY dem_voters DESC
""", (ELECTION_DATE,))

for row in cursor.fetchall():
    print(f"  {row['congressional_district']}: {row['dem_voters']:,} Democratic voters")

# Check the official D15 number
print("\n" + "=" * 80)
print("D15 TOTAL (ALL COUNTIES)")
print("=" * 80)

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    WHERE ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.congressional_district = 'TX-15'
""", (ELECTION_DATE,))

current_d15 = cursor.fetchone()[0]
official_d15 = 54573

print(f"\nCurrent D15 assignment:  {current_d15:,}")
print(f"Official D15 count:      {official_d15:,}")
print(f"Difference:              {official_d15 - current_d15:+,}")

conn.close()
