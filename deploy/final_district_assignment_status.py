#!/usr/bin/env python3
"""
FINAL DISTRICT ASSIGNMENT STATUS REPORT

Shows exactly what we have, what's working, and what's missing.
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("DISTRICT ASSIGNMENT - FINAL STATUS REPORT")
print("=" * 80)

# Overall stats
print("\n1. OVERALL VOTING RECORDS")
print("-" * 80)

cursor.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = ?", (ELECTION_DATE,))
total_votes = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) FROM voter_elections 
    WHERE election_date = ? AND precinct IS NOT NULL AND precinct != ''
""", (ELECTION_DATE,))
with_precinct = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) FROM voter_elections 
    WHERE election_date = ? AND congressional_district IS NOT NULL AND congressional_district != ''
""", (ELECTION_DATE,))
with_district = cursor.fetchone()[0]

print(f"Total voting records:           {total_votes:>12,}")
print(f"Records with precinct data:     {with_precinct:>12,} ({100*with_precinct/total_votes:>5.1f}%)")
print(f"Records assigned to districts:  {with_district:>12,} ({100*with_district/total_votes:>5.1f}%)")
print(f"Records WITHOUT precinct data:  {total_votes-with_precinct:>12,} ({100*(total_votes-with_precinct)/total_votes:>5.1f}%)")

# D15 specific
print("\n2. D15 (CONGRESSIONAL DISTRICT 15)")
print("-" * 80)

d15_counties = ['Hidalgo', 'Brooks', 'Jim Wells', 'Bee', 'San Patricio', 'Refugio']

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county IN ('Hidalgo', 'Brooks', 'Jim Wells', 'Bee', 'San Patricio', 'Refugio')
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
""", (ELECTION_DATE,))
total_d15 = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    WHERE ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.congressional_district = 'TX-15'
""", (ELECTION_DATE,))
assigned_d15 = cursor.fetchone()[0]

official_d15 = 54573

print(f"Total Dem voters in D15 counties:  {total_d15:>12,}")
print(f"Assigned to TX-15:                 {assigned_d15:>12,}")
print(f"Official TX-15 count:              {official_d15:>12,}")
print(f"Difference:                        {assigned_d15 - official_d15:>+12,}")
print(f"Accuracy:                          {100*(1-abs(assigned_d15-official_d15)/official_d15):>11.1f}%")

# By county
print("\nD15 Counties - Detailed Breakdown:")
print(f"{'County':<20} {'Total Dem':>12} {'With Precinct':>15} {'Assigned TX-15':>15}")
print("-" * 80)

for county in d15_counties:
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
    """, (county, ELECTION_DATE))
    total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
        AND ve.precinct IS NOT NULL
        AND ve.precinct != ''
    """, (county, ELECTION_DATE))
    with_prec = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
        AND ve.congressional_district = 'TX-15'
    """, (county, ELECTION_DATE))
    assigned = cursor.fetchone()[0]
    
    prec_pct = f"({100*with_prec/total:.1f}%)" if total > 0 else ""
    assign_pct = f"({100*assigned/total:.1f}%)" if total > 0 else ""
    
    print(f"{county:<20} {total:>12,} {with_prec:>10,} {prec_pct:>4} {assigned:>10,} {assign_pct:>4}")

# Root cause analysis
print("\n3. ROOT CAUSE ANALYSIS")
print("-" * 80)

print("\nWhy are we short 37,636 D15 voters?")
print("\nHypothesis 1: Missing precinct data in voter_elections table")

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county IN ('Hidalgo', 'Brooks', 'Jim Wells', 'Bee', 'San Patricio', 'Refugio')
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND (ve.precinct IS NULL OR ve.precinct = '')
""", (ELECTION_DATE,))
no_precinct = cursor.fetchone()[0]

print(f"  D15 voters WITHOUT precinct data: {no_precinct:,}")
print(f"  This accounts for: {100*no_precinct/(official_d15-assigned_d15):.1f}% of missing voters")

print("\nHypothesis 2: Precinct format mismatch")
print("  Reference data uses: '0001', '0002', '0003' (4 digits, leading zeros)")
print("  Voting records use:  '151', '226', '114' (2-3 digits, no leading zeros)")
print("  Our normalizer handles this, but only if precinct data exists")

print("\nHypothesis 3: Data source differences")
cursor.execute("""
    SELECT data_source, COUNT(DISTINCT vuid) as count
    FROM voter_elections
    WHERE election_date = ?
    AND party_voted = 'Democratic'
    GROUP BY data_source
    ORDER BY count DESC
""", (ELECTION_DATE,))

print("\n  Voting records by data source:")
for source, count in cursor.fetchall():
    print(f"    {source or 'NULL':<30} {count:>10,}")

# Solution
print("\n4. SOLUTION")
print("-" * 80)
print("\nTo achieve 100% accuracy, we need to:")
print("\n  Option A: Get precinct data for the 883,422 voters who don't have it")
print("    - Re-scrape from Texas SOS with precinct field")
print("    - Or use county-level uploads that include precinct")
print("\n  Option B: Use geographic matching for voters without precinct data")
print("    - Use voter lat/lng + district shapefiles")
print("    - Point-in-polygon matching")
print("    - Requires geocoding remaining voters")
print("\n  Option C: Accept current accuracy and use county-level fallback")
print("    - For split counties, this will be inaccurate")
print("    - Not recommended per user requirements")

print("\n" + "=" * 80)
print("RECOMMENDATION: Option A - Get precinct data for all voters")
print("=" * 80)

conn.close()
