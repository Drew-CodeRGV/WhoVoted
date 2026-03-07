#!/usr/bin/env python3
"""
Verify all voter data is loaded and usable across all districts
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("="*80)
print("COMPLETE VOTER DATA VERIFICATION")
print("="*80)

# Total registered voters
cursor.execute("SELECT COUNT(*) FROM voters")
total_voters = cursor.fetchone()[0]
print(f"\nTotal registered voters in database: {total_voters:,}")

# Voters with district assignments
cursor.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN congressional_district IS NOT NULL AND congressional_district != '' THEN 1 END) as with_cd,
        COUNT(CASE WHEN state_senate_district IS NOT NULL AND state_senate_district != '' THEN 1 END) as with_sd,
        COUNT(CASE WHEN state_house_district IS NOT NULL AND state_house_district != '' THEN 1 END) as with_hd
    FROM voters
""")
row = cursor.fetchone()
print(f"\nDistrict Assignment Coverage:")
print(f"  Congressional: {row[1]:,} / {row[0]:,} ({100*row[1]/row[0]:.2f}%)")
print(f"  State Senate:  {row[2]:,} / {row[0]:,} ({100*row[2]/row[0]:.2f}%)")
print(f"  State House:   {row[3]:,} / {row[0]:,} ({100*row[3]/row[0]:.2f}%)")

# Total voter_elections records
cursor.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = '2026-03-03'")
total_records = cursor.fetchone()[0]
print(f"\nTotal 2026-03-03 election records: {total_records:,}")

# Unique voters who voted
cursor.execute("""
    SELECT COUNT(DISTINCT vuid) 
    FROM voter_elections 
    WHERE election_date = '2026-03-03'
""")
unique_voters = cursor.fetchone()[0]
print(f"Unique voters who voted: {unique_voters:,}")

# By party
print("\n" + "-"*80)
print("VOTES BY PARTY")
print("-"*80)
cursor.execute("""
    SELECT 
        party_voted,
        COUNT(DISTINCT vuid) as unique_voters,
        COUNT(*) as total_records
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    AND party_voted != '' AND party_voted IS NOT NULL
    GROUP BY party_voted
    ORDER BY unique_voters DESC
""")
for party, unique, total in cursor.fetchall():
    print(f"{party:<15} {unique:>10,} voters  {total:>10,} records")

# D15 specific check
print("\n" + "-"*80)
print("D15 DEMOCRATIC PRIMARY VERIFICATION")
print("-"*80)
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
""")
d15_dem = cursor.fetchone()[0]
print(f"D15 Democratic voters: {d15_dem:,}")
print(f"Official count: 54,573")
print(f"Match: {'✓ YES' if d15_dem == 54573 else f'✗ NO (off by {d15_dem - 54573:,})'}")

# Top 10 congressional districts by Democratic turnout
print("\n" + "-"*80)
print("TOP 10 CONGRESSIONAL DISTRICTS (Democratic Primary)")
print("-"*80)
cursor.execute("""
    SELECT 
        v.congressional_district,
        COUNT(DISTINCT ve.vuid) as dem_voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    AND v.congressional_district IS NOT NULL
    AND v.congressional_district != ''
    GROUP BY v.congressional_district
    ORDER BY dem_voters DESC
    LIMIT 10
""")
print(f"{'District':<12} {'Dem Voters':>12}")
print("-"*25)
for district, voters in cursor.fetchall():
    print(f"TX-{district:<9} {voters:>12,}")

# Data source breakdown
print("\n" + "-"*80)
print("DATA SOURCES")
print("-"*80)
cursor.execute("""
    SELECT 
        COALESCE(data_source, 'NULL') as source,
        COUNT(DISTINCT vuid) as unique_voters,
        COUNT(*) as total_records
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    GROUP BY data_source
    ORDER BY unique_voters DESC
""")
for source, unique, total in cursor.fetchall():
    print(f"{source:<25} {unique:>10,} voters  {total:>10,} records")

conn.close()

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
