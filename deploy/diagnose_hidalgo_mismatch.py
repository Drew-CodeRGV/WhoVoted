#!/usr/bin/env python3
"""
Diagnose why Hidalgo precincts aren't matching to D15
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("HIDALGO PRECINCT MATCHING DIAGNOSIS")
print("=" * 80)

# 1. How many Hidalgo Democratic voters do we have?
print("\n1. HIDALGO DEMOCRATIC VOTERS")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND (ve.data_source IS NULL OR ve.data_source NOT LIKE 'obsolete%')
""", (ELECTION_DATE,))

total_hidalgo_dem = cursor.fetchone()[0]
print(f"Total Hidalgo Democratic voters: {total_hidalgo_dem:,}")

# 2. How many have precinct data?
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.precinct IS NOT NULL
    AND ve.precinct != ''
    AND (ve.data_source IS NULL OR ve.data_source NOT LIKE 'obsolete%')
""", (ELECTION_DATE,))

with_precinct = cursor.fetchone()[0]
print(f"With precinct data:              {with_precinct:,} ({100*with_precinct/total_hidalgo_dem:.1f}%)")

# 3. How many are assigned to D15?
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
print(f"Assigned to TX-15:               {assigned_d15:,} ({100*assigned_d15/total_hidalgo_dem:.1f}%)")

# 4. Sample Hidalgo precincts from voting records
print("\n2. SAMPLE HIDALGO PRECINCTS (Voting Records)")
print("-" * 80)

cursor.execute("""
    SELECT DISTINCT ve.precinct, COUNT(*) as count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.precinct IS NOT NULL
    AND ve.precinct != ''
    AND (ve.data_source IS NULL OR ve.data_source NOT LIKE 'obsolete%')
    GROUP BY ve.precinct
    ORDER BY count DESC
    LIMIT 20
""", (ELECTION_DATE,))

print(f"{'Precinct':<20} {'Voters':>10}")
print("-" * 32)
for row in cursor.fetchall():
    print(f"{row['precinct']:<20} {row['count']:>10,}")

# 5. Sample Hidalgo precincts from reference data
print("\n3. SAMPLE HIDALGO PRECINCTS (Reference Data)")
print("-" * 80)

cursor.execute("""
    SELECT DISTINCT precinct, congressional_district
    FROM precinct_districts
    WHERE county = 'Hidalgo'
    AND congressional_district = '15'
    ORDER BY precinct
    LIMIT 20
""")

print(f"{'Precinct':<20} {'District':>10}")
print("-" * 32)
for row in cursor.fetchall():
    print(f"{row['precinct']:<20} {row['congressional_district']:>10}")

# 6. Check normalized variants
print("\n4. NORMALIZED VARIANTS FOR HIDALGO")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(DISTINCT original_precinct)
    FROM precinct_normalized
    WHERE county = 'Hidalgo'
    AND congressional_district = '15'
""")

hidalgo_precincts_in_ref = cursor.fetchone()[0]
print(f"Hidalgo precincts in reference (D15): {hidalgo_precincts_in_ref:,}")

cursor.execute("""
    SELECT COUNT(*)
    FROM precinct_normalized
    WHERE county = 'Hidalgo'
    AND congressional_district = '15'
""")

hidalgo_variants = cursor.fetchone()[0]
print(f"Total normalized variants:             {hidalgo_variants:,}")

# 7. Try to match a specific precinct manually
print("\n5. MANUAL MATCHING TEST")
print("-" * 80)

# Get a common Hidalgo precinct from voting records
cursor.execute("""
    SELECT ve.precinct, COUNT(*) as count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.precinct IS NOT NULL
    AND ve.precinct != ''
    AND (ve.data_source IS NULL OR ve.data_source NOT LIKE 'obsolete%')
    GROUP BY ve.precinct
    ORDER BY count DESC
    LIMIT 1
""", (ELECTION_DATE,))

test_precinct = cursor.fetchone()
if test_precinct:
    precinct_name = test_precinct['precinct']
    voter_count = test_precinct['count']
    
    print(f"Testing precinct: '{precinct_name}' ({voter_count:,} voters)")
    
    # Try to find it in normalized table
    cursor.execute("""
        SELECT normalized_precinct, congressional_district
        FROM precinct_normalized
        WHERE county = 'Hidalgo'
        AND original_precinct = ?
        LIMIT 5
    """, (precinct_name,))
    
    matches = cursor.fetchall()
    if matches:
        print(f"Found {len(matches)} matches in normalized table:")
        for match in matches:
            print(f"  Normalized: '{match['normalized_precinct']}' → District: {match['congressional_district']}")
    else:
        print("  ✗ NOT FOUND in normalized table")
        
        # Try fuzzy search
        print("\n  Searching for similar precincts in reference data:")
        cursor.execute("""
            SELECT DISTINCT precinct
            FROM precinct_districts
            WHERE county = 'Hidalgo'
            AND precinct LIKE ?
            LIMIT 10
        """, (f"%{precinct_name[:3]}%",))
        
        similar = cursor.fetchall()
        if similar:
            for s in similar:
                print(f"    Similar: '{s['precinct']}'")

# 8. Check if the issue is county name mismatch
print("\n6. COUNTY NAME CHECK")
print("-" * 80)

cursor.execute("""
    SELECT DISTINCT county
    FROM precinct_districts
    WHERE county LIKE '%Hidalgo%' OR county LIKE '%hidalgo%'
""")

counties = cursor.fetchall()
print("Counties in reference data matching 'Hidalgo':")
for c in counties:
    print(f"  '{c['county']}'")

cursor.execute("""
    SELECT DISTINCT v.county
    FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county LIKE '%Hidalgo%' OR v.county LIKE '%hidalgo%'
    AND ve.election_date = ?
    LIMIT 5
""", (ELECTION_DATE,))

counties = cursor.fetchall()
print("\nCounties in voters table matching 'Hidalgo':")
for c in counties:
    print(f"  '{c['county']}'")

conn.close()
