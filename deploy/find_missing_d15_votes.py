#!/usr/bin/env python3
"""Find the missing 5,243 Democratic votes in D15"""
import sqlite3

conn = sqlite3.connect('data/whovoted.db')
c = conn.cursor()

print("="*80)
print("FINDING MISSING D15 DEMOCRATIC VOTES")
print("="*80)
print("\nExpected: 54,573 Democratic votes")
print("Found:    49,330 Democratic votes")
print("Missing:   5,243 votes")

# Check if there are voters in Hidalgo County who voted Dem but aren't in TX-15
print("\n" + "="*80)
print("HIDALGO COUNTY VOTERS NOT IN TX-15")
print("="*80)

c.execute("""
    SELECT 
        v.congressional_district,
        COUNT(DISTINCT ve.vuid) as votes
    FROM voter_elections ve 
    JOIN voters v ON ve.vuid = v.vuid 
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = '2026-03-03' 
    AND ve.party_voted = 'Democratic'
    GROUP BY v.congressional_district
    ORDER BY votes DESC
""")

print("\nHidalgo County Democratic votes by district:")
print("-" * 80)
hidalgo_total = 0
for row in c.fetchall():
    district = row[0] if row[0] else 'NULL/Unassigned'
    votes = row[1]
    hidalgo_total += votes
    marker = " ← TX-15" if row[0] == '15' else ""
    print(f"  TX-{district:10s}: {votes:6,} votes{marker}")

print(f"\nTotal Hidalgo Dem votes: {hidalgo_total:,}")

# Check for voters with NULL district
print("\n" + "="*80)
print("VOTERS WITH NO DISTRICT ASSIGNMENT")
print("="*80)

c.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve 
    JOIN voters v ON ve.vuid = v.vuid 
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = '2026-03-03' 
    AND ve.party_voted = 'Democratic'
    AND v.congressional_district IS NULL
""")
unassigned = c.fetchone()[0]
print(f"\nHidalgo Dem voters with no district: {unassigned:,}")

# Check all counties that should be in TX-15
print("\n" + "="*80)
print("ALL TX-15 COUNTIES - DEMOCRATIC VOTES")
print("="*80)

tx15_counties = ['Hidalgo', 'Brooks', 'Bee', 'DeWitt', 'Goliad', 'Gonzales', 
                 'Jim Wells', 'Karnes', 'Lavaca', 'Live Oak', 'Aransas']

print("\nExpected TX-15 counties:")
total_by_county = 0
for county in tx15_counties:
    c.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve 
        JOIN voters v ON ve.vuid = v.vuid 
        WHERE v.county = ?
        AND ve.election_date = '2026-03-03' 
        AND ve.party_voted = 'Democratic'
    """, [county])
    votes = c.fetchone()[0]
    total_by_county += votes
    
    # Check how many are assigned to TX-15
    c.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve 
        JOIN voters v ON ve.vuid = v.vuid 
        WHERE v.county = ?
        AND v.congressional_district = '15'
        AND ve.election_date = '2026-03-03' 
        AND ve.party_voted = 'Democratic'
    """, [county])
    in_tx15 = c.fetchone()[0]
    
    missing = votes - in_tx15
    marker = f" (missing {missing})" if missing > 0 else ""
    print(f"  {county:20s}: {votes:6,} total, {in_tx15:6,} in TX-15{marker}")

print(f"\nTotal across all TX-15 counties: {total_by_county:,}")
print(f"Total assigned to TX-15:         {49330:,}")
print(f"Difference:                      {total_by_county - 49330:,}")

# Check if voters are assigned to wrong districts
print("\n" + "="*80)
print("VOTERS IN TX-15 COUNTIES BUT ASSIGNED TO OTHER DISTRICTS")
print("="*80)

for county in tx15_counties:
    c.execute("""
        SELECT 
            v.congressional_district,
            COUNT(DISTINCT ve.vuid) as votes
        FROM voter_elections ve 
        JOIN voters v ON ve.vuid = v.vuid 
        WHERE v.county = ?
        AND ve.election_date = '2026-03-03' 
        AND ve.party_voted = 'Democratic'
        AND v.congressional_district != '15'
        AND v.congressional_district IS NOT NULL
        GROUP BY v.congressional_district
        ORDER BY votes DESC
    """, [county])
    
    results = c.fetchall()
    if results:
        print(f"\n{county}:")
        for row in results:
            print(f"  TX-{row[0]}: {row[1]:,} votes")

conn.close()

print("\n" + "="*80)
print("SUMMARY")
print("="*80)
print(f"\nExpected D15 Dem votes: 54,573")
print(f"Found in database:      49,330")
print(f"Missing:                 5,243")
print("\nPossible reasons:")
print("  1. Voters in TX-15 counties assigned to wrong districts")
print("  2. Missing voter data not yet imported")
print("  3. Voters with no district assignment")
print("  4. Expected number includes voters not in database")
