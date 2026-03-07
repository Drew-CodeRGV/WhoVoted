#!/usr/bin/env python3
"""
Check Hidalgo precinct coverage in detail
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("HIDALGO PRECINCT COVERAGE ANALYSIS")
print("=" * 80)

# Total Hidalgo voters
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
""", (ELECTION_DATE,))

total = cursor.fetchone()[0]

# With precinct
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.precinct IS NOT NULL
    AND ve.precinct != ''
""", (ELECTION_DATE,))

with_precinct = cursor.fetchone()[0]

# Without precinct
without_precinct = total - with_precinct

print(f"\nHidalgo Democratic Voters:")
print(f"  Total:           {total:>10,}")
print(f"  With precinct:   {with_precinct:>10,} ({100*with_precinct/total:.1f}%)")
print(f"  Without precinct:{without_precinct:>10,} ({100*without_precinct/total:.1f}%)")

# Check if voters table has precinct data
print(f"\n" + "=" * 80)
print("CHECKING VOTERS TABLE FOR PRECINCT DATA")
print("=" * 80)

cursor.execute("""
    SELECT COUNT(DISTINCT v.vuid)
    FROM voters v
    WHERE v.county = 'Hidalgo'
    AND v.precinct IS NOT NULL
    AND v.precinct != ''
""")

voters_with_precinct = cursor.fetchone()[0]

print(f"\nVoters in 'voters' table with precinct: {voters_with_precinct:,}")

# Sample voters without precinct in voter_elections
print(f"\n" + "=" * 80)
print("SAMPLE VOTERS WITHOUT PRECINCT IN VOTER_ELECTIONS")
print("=" * 80)

cursor.execute("""
    SELECT 
        ve.vuid,
        v.precinct as voter_precinct,
        ve.precinct as election_precinct,
        ve.data_source,
        ve.source_file
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND (ve.precinct IS NULL OR ve.precinct = '')
    LIMIT 10
""", (ELECTION_DATE,))

print(f"\n{'VUID':<15} {'Voter Prec':<12} {'Elec Prec':<12} {'Data Source':<20} {'Source File':<30}")
print("-" * 100)

for row in cursor.fetchall():
    voter_prec = row['voter_precinct'] or 'NULL'
    elec_prec = row['election_precinct'] or 'NULL'
    source = (row['data_source'] or 'NULL')[:18]
    file = (row['source_file'] or 'NULL')[:28]
    print(f"{row['vuid']:<15} {voter_prec:<12} {elec_prec:<12} {source:<20} {file:<30}")

# Check if we can copy precinct from voters to voter_elections
print(f"\n" + "=" * 80)
print("POTENTIAL FIX: COPY PRECINCT FROM VOTERS TABLE")
print("=" * 80)

cursor.execute("""
    SELECT COUNT(*)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND (ve.precinct IS NULL OR ve.precinct = '')
    AND v.precinct IS NOT NULL
    AND v.precinct != ''
""", (ELECTION_DATE,))

can_fix = cursor.fetchone()[0]

print(f"\nVoters without precinct in voter_elections")
print(f"but WITH precinct in voters table: {can_fix:,}")

if can_fix > 0:
    print(f"\n✓ We can copy precinct data from voters table to fix {can_fix:,} records!")

conn.close()
