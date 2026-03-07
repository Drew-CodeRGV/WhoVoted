#!/usr/bin/env python3
"""
Fix wrong district assignments by using precinct_districts table
Remove county-level fallback assignments that are incorrect
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH, timeout=60.0)
cursor = conn.cursor()

print("="*80)
print("FIXING WRONG DISTRICT ASSIGNMENTS")
print("="*80)

# Check precinct_districts table
print("\n[1] Checking precinct_districts table...")
cursor.execute("SELECT COUNT(*) FROM precinct_districts")
precinct_count = cursor.fetchone()[0]
print(f"  Precinct mappings available: {precinct_count:,}")

# Find voters with wrong districts (in counties that shouldn't be in their assigned district)
print("\n[2] Finding voters with incorrect district assignments...")

# D15 should only be in these counties (full or partial)
D15_COUNTIES = ['Hidalgo', 'Cameron', 'Willacy', 'Brooks', 'Jim Hogg', 'Kenedy', 'Kleberg', 'Starr', 'Zapata', 'Nueces', 'Webb']

# Find D15 voters NOT in D15 counties
cursor.execute("""
    SELECT 
        v.county,
        COUNT(*) as voter_count
    FROM voters v
    WHERE v.congressional_district = '15'
    AND v.county NOT IN ('Hidalgo', 'Cameron', 'Willacy', 'Brooks', 'Jim Hogg', 'Kenedy', 'Kleberg', 'Starr', 'Zapata', 'Nueces', 'Webb')
    GROUP BY v.county
    ORDER BY voter_count DESC
""")

wrong_counties = cursor.fetchall()
if wrong_counties:
    print(f"\n  Found voters in {len(wrong_counties)} counties that shouldn't be in D15:")
    total_wrong = 0
    for county, count in wrong_counties:
        print(f"    {county}: {count:,} voters")
        total_wrong += count
    print(f"\n  Total voters to fix: {total_wrong:,}")
else:
    print("  No incorrect assignments found")
    conn.close()
    exit(0)

# Strategy: Set congressional_district to NULL for voters in wrong counties
# They'll need to be reassigned using precinct data
print("\n[3] Clearing incorrect district assignments...")
cursor.execute("""
    UPDATE voters
    SET congressional_district = NULL,
        state_senate_district = NULL,
        state_house_district = NULL
    WHERE congressional_district = '15'
    AND county NOT IN ('Hidalgo', 'Cameron', 'Willacy', 'Brooks', 'Jim Hogg', 'Kenedy', 'Kleberg', 'Starr', 'Zapata', 'Nueces', 'Webb')
""")

cleared = cursor.rowcount
print(f"  Cleared districts for {cleared:,} voters")

conn.commit()

# Now try to reassign using precinct data
print("\n[4] Reassigning using precinct data...")
cursor.execute("""
    UPDATE voters
    SET congressional_district = (
        SELECT pd.congressional_district
        FROM precinct_districts pd
        WHERE pd.county = voters.county
        AND pd.precinct = voters.precinct
        LIMIT 1
    ),
    state_senate_district = (
        SELECT pd.state_senate_district
        FROM precinct_districts pd
        WHERE pd.county = voters.county
        AND pd.precinct = voters.precinct
        LIMIT 1
    ),
    state_house_district = (
        SELECT pd.state_house_district
        FROM precinct_districts pd
        WHERE pd.county = voters.county
        AND pd.precinct = voters.precinct
        LIMIT 1
    )
    WHERE congressional_district IS NULL
    AND precinct IS NOT NULL
    AND precinct != ''
    AND EXISTS (
        SELECT 1 FROM precinct_districts pd
        WHERE pd.county = voters.county
        AND pd.precinct = voters.precinct
    )
""")

reassigned = cursor.rowcount
print(f"  Reassigned {reassigned:,} voters using precinct data")

conn.commit()

# Check how many are still unassigned
cursor.execute("""
    SELECT COUNT(*)
    FROM voters
    WHERE congressional_district IS NULL
""")
still_unassigned = cursor.fetchone()[0]
print(f"  Still unassigned: {still_unassigned:,} voters")

# Verify D15 count
print("\n[5] Verifying D15 Democratic count...")
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
""")

d15_count = cursor.fetchone()[0]
print(f"  D15 Democratic voters: {d15_count:,}")
print(f"  Official count: 54,573")
print(f"  Difference: {d15_count - 54573:,}")

if d15_count == 54573:
    print(f"  ✓ EXACT MATCH!")
elif abs(d15_count - 54573) < 100:
    print(f"  ~ Close (within 100)")
else:
    print(f"  Still off by {abs(d15_count - 54573):,}")

# Show D15 counties breakdown
print("\n[6] D15 voters by county:")
cursor.execute("""
    SELECT 
        v.county,
        COUNT(DISTINCT ve.vuid) as voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY v.county
    ORDER BY voters DESC
""")

for county, voters in cursor.fetchall():
    in_list = "✓" if county in D15_COUNTIES else "✗"
    print(f"  {in_list} {county:<20} {voters:>8,}")

conn.close()

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
