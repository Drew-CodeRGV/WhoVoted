#!/usr/bin/env python3
"""
Verify the reality of Hidalgo voter counts
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("HIDALGO VOTER REALITY CHECK")
print("=" * 80)

# Total Hidalgo voters (all data sources)
print("\n1. ALL HIDALGO VOTERS (Including Obsolete)")
print("-" * 80)

cursor.execute("""
    SELECT 
        ve.data_source,
        COUNT(DISTINCT ve.vuid) as voters,
        COUNT(CASE WHEN ve.party_voted = 'Democratic' THEN 1 END) as dem_votes
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    GROUP BY ve.data_source
    ORDER BY voters DESC
""", (ELECTION_DATE,))

print(f"{'Data Source':<30} {'Voters':>10} {'Dem Votes':>12}")
print("-" * 54)

total_voters = 0
total_dem = 0
obsolete_dem = 0

for row in cursor.fetchall():
    source = row['data_source'] or 'NULL'
    print(f"{source:<30} {row['voters']:>10,} {row['dem_votes']:>12,}")
    total_voters += row['voters']
    total_dem += row['dem_votes']
    
    if row['data_source'] and 'obsolete' in row['data_source']:
        obsolete_dem += row['dem_votes']

print("-" * 54)
print(f"{'TOTAL':<30} {total_voters:>10,} {total_dem:>12,}")
print(f"{'Obsolete Democratic':<30} {'':<10} {obsolete_dem:>12,}")

# Current (non-obsolete) Hidalgo voters
print("\n2. CURRENT HIDALGO VOTERS (Excluding Obsolete)")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND (ve.data_source IS NULL OR ve.data_source NOT LIKE 'obsolete%')
""", (ELECTION_DATE,))

current_total = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND (ve.data_source IS NULL OR ve.data_source NOT LIKE 'obsolete%')
""", (ELECTION_DATE,))

current_dem = cursor.fetchone()[0]

print(f"Current total voters:      {current_total:,}")
print(f"Current Democratic voters: {current_dem:,}")

# D15 assignment status
print("\n3. D15 ASSIGNMENT STATUS")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.congressional_district = 'TX-15'
    AND (ve.data_source IS NULL OR ve.data_source NOT LIKE 'obsolete%')
""", (ELECTION_DATE,))

assigned_d15 = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND (ve.congressional_district IS NULL OR ve.congressional_district = '')
    AND (ve.data_source IS NULL OR ve.data_source NOT LIKE 'obsolete%')
""", (ELECTION_DATE,))

unassigned = cursor.fetchone()[0]

print(f"Assigned to TX-15:         {assigned_d15:,} ({100*assigned_d15/current_dem:.1f}%)")
print(f"Unassigned:                {unassigned:,} ({100*unassigned/current_dem:.1f}%)")

# Check if unassigned voters have precinct data
print("\n4. UNASSIGNED VOTERS - DO THEY HAVE PRECINCTS?")
print("-" * 80)

cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN ve.precinct IS NOT NULL AND ve.precinct != '' THEN 1 END) as with_precinct
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND (ve.congressional_district IS NULL OR ve.congressional_district = '')
    AND (ve.data_source IS NULL OR ve.data_source NOT LIKE 'obsolete%')
""", (ELECTION_DATE,))

row = cursor.fetchone()
print(f"Unassigned voters:         {row['total']:,}")
print(f"With precinct data:        {row['with_precinct']:,}")

if row['with_precinct'] > 0:
    print("\n  Sample unassigned precincts:")
    cursor.execute("""
        SELECT DISTINCT ve.precinct, COUNT(*) as count
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
        AND (ve.congressional_district IS NULL OR ve.congressional_district = '')
        AND ve.precinct IS NOT NULL
        AND ve.precinct != ''
        AND (ve.data_source IS NULL OR ve.data_source NOT LIKE 'obsolete%')
        GROUP BY ve.precinct
        ORDER BY count DESC
        LIMIT 10
    """, (ELECTION_DATE,))
    
    for row in cursor.fetchall():
        print(f"    Precinct '{row['precinct']}': {row['count']:,} voters")

# The big question
print("\n5. THE BIG QUESTION")
print("-" * 80)

official_d15 = 54573
print(f"Official D15 count:        {official_d15:,}")
print(f"Current Hidalgo Dem:       {current_dem:,}")
print(f"Difference:                {official_d15 - current_dem:+,}")

if current_dem < official_d15:
    print(f"\n⚠ We're missing {official_d15 - current_dem:,} Hidalgo Democratic voters in our data!")
    print("  This means the scrapers didn't capture all voters, OR")
    print("  D15 includes voters from other counties that we haven't counted yet.")

conn.close()
