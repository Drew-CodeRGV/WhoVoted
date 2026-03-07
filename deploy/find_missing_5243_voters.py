#!/usr/bin/env python3
"""Find the missing 5,243 D15 Democratic voters"""
import sqlite3

conn = sqlite3.connect('data/whovoted.db')
c = conn.cursor()

print("="*80)
print("FINDING THE MISSING 5,243 D15 DEMOCRATIC VOTERS")
print("="*80)
print("\nOfficial D15 Dem ballots cast: 54,573")
print("Database has:                  49,330")
print("Missing:                        5,243 (9.6%)")

# Check 1: Are there voters in TX-15 who voted Dem but in a different election?
print("\n" + "="*80)
print("CHECK 1: VOTERS IN TX-15 WHO VOTED DEM IN OTHER ELECTIONS")
print("="*80)

c.execute("""
    SELECT ve.election_date, COUNT(DISTINCT ve.vuid) as voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.election_date
    ORDER BY ve.election_date DESC
""")

print("\nTX-15 Dem voters by election date:")
print("-" * 80)
for row in c.fetchall():
    print(f"  {row[0]}: {row[1]:,} voters")

# Check 2: Are there voters in the database who aren't in voter_elections yet?
print("\n" + "="*80)
print("CHECK 2: REGISTERED VOTERS IN TX-15 NOT IN VOTER_ELECTIONS")
print("="*80)

c.execute("""
    SELECT COUNT(*)
    FROM voters v
    WHERE v.congressional_district = '15'
""")
total_registered = c.fetchone()[0]

c.execute("""
    SELECT COUNT(DISTINCT v.vuid)
    FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
""")
voted_2026 = c.fetchone()[0]

not_in_election = total_registered - voted_2026

print(f"\nTotal registered voters in TX-15: {total_registered:,}")
print(f"Voted in 2026-03-03:               {voted_2026:,}")
print(f"Not in 2026-03-03 election:        {not_in_election:,}")

# Check 3: What data sources do we have for 2026-03-03?
print("\n" + "="*80)
print("CHECK 3: DATA SOURCES FOR 2026-03-03 ELECTION")
print("="*80)

c.execute("""
    SELECT data_source, COUNT(DISTINCT ve.vuid) as voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY data_source
    ORDER BY voters DESC
""")

print("\nData sources for TX-15 Dem voters in 2026-03-03:")
print("-" * 80)
for row in c.fetchall():
    source = row[0] if row[0] else 'NULL'
    print(f"  {source:30s}: {row[1]:,} voters")

# Check 4: Are there voters with no district assignment who should be in TX-15?
print("\n" + "="*80)
print("CHECK 4: VOTERS WITH NO DISTRICT WHO VOTED DEM 2026-03-03")
print("="*80)

c.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district IS NULL
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
""")
no_district = c.fetchone()[0]

print(f"\nDem voters with no district assignment: {no_district:,}")

if no_district > 0:
    c.execute("""
        SELECT v.county, COUNT(DISTINCT ve.vuid) as voters
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.congressional_district IS NULL
        AND ve.election_date = '2026-03-03'
        AND ve.party_voted = 'Democratic'
        GROUP BY v.county
        ORDER BY voters DESC
        LIMIT 10
    """)
    print("\nTop counties with unassigned Dem voters:")
    print("-" * 80)
    for row in c.fetchall():
        print(f"  {row[0]:20s}: {row[1]:,} voters")

# Check 5: Check if there are files not yet imported
print("\n" + "="*80)
print("CHECK 5: TOTAL VOTERS IN DATABASE FOR 2026-03-03")
print("="*80)

c.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as total,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
    FROM voter_elections ve
    WHERE ve.election_date = '2026-03-03'
""")
row = c.fetchone()

print(f"\nTotal voters in 2026-03-03 election:")
print(f"  Total:      {row[0]:,}")
print(f"  Democratic: {row[1]:,}")
print(f"  Republican: {row[2]:,}")

conn.close()

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)
print("\nTo find the missing 5,243 voters, we need to:")
print("  1. Check if there are additional voter files to import")
print("  2. Verify all counties have complete data for 2026-03-03")
print("  3. Check if some voters are in the database but not in voter_elections")
print("  4. Verify the data source matches the official election results")
