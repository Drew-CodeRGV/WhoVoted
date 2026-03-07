#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cursor = conn.cursor()

print("=" * 70)
print("HIDALGO COUNTY PRECINCT FORMAT COMPARISON")
print("=" * 70)

print("\nReference Data (precinct_districts):")
print("Sample precincts for District 15:")
cursor.execute("""
    SELECT DISTINCT precinct
    FROM precinct_districts
    WHERE county = 'Hidalgo' AND congressional_district = '15'
    ORDER BY precinct
    LIMIT 20
""")
for (precinct,) in cursor.fetchall():
    print(f"  '{precinct}'")

print("\nVoting Records (voter_elections):")
print("Top precincts by Democratic voter count:")
cursor.execute("""
    SELECT ve.precinct, COUNT(*) as count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    AND ve.precinct IS NOT NULL
    AND ve.precinct != ''
    GROUP BY ve.precinct
    ORDER BY count DESC
    LIMIT 20
""")
for precinct, count in cursor.fetchall():
    print(f"  '{precinct}' - {count:,} voters")

print("\nTotal Hidalgo Democratic voters:")
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
""")
total = cursor.fetchone()[0]
print(f"  {total:,}")

print("\nHidalgo voters WITH precinct data:")
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    AND ve.precinct IS NOT NULL
    AND ve.precinct != ''
""")
with_precinct = cursor.fetchone()[0]
print(f"  {with_precinct:,} ({100*with_precinct/total:.1f}%)")

print("\nHidalgo voters ASSIGNED to TX-15:")
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    AND ve.congressional_district = 'TX-15'
""")
assigned = cursor.fetchone()[0]
print(f"  {assigned:,} ({100*assigned/total:.1f}%)")

conn.close()
