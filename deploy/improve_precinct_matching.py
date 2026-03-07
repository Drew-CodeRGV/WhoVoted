#!/usr/bin/env python3
"""
IMPROVE PRECINCT MATCHING

Analyze top unmatched precincts and add manual mappings where possible.
Focus on high-volume precincts to maximize impact.
"""
import sqlite3
import re

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("IMPROVING PRECINCT MATCHING")
print("=" * 80)

# Get top unmatched precincts
print("\n1. TOP UNMATCHED PRECINCTS")
print("-" * 80)

cursor.execute("""
    SELECT 
        v.county,
        ve.precinct,
        COUNT(*) as voter_count,
        ve.party_voted
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = ?
    AND ve.precinct IS NOT NULL 
    AND ve.precinct != ''
    AND (ve.congressional_district IS NULL OR ve.congressional_district = '')
    GROUP BY v.county, ve.precinct, ve.party_voted
    ORDER BY voter_count DESC
    LIMIT 30
""", (ELECTION_DATE,))

unmatched = cursor.fetchall()

print(f"{'County':<20} {'Precinct':<20} {'Party':<12} {'Voters':>8}")
print("-" * 62)

for row in unmatched:
    print(f"{row['county']:<20} {row['precinct']:<20} {row['party_voted']:<12} {row['voter_count']:>8,}")

# For each top unmatched precinct, try to find similar precincts in reference data
print("\n2. FINDING POTENTIAL MATCHES")
print("-" * 80)

manual_mappings = []

for row in unmatched[:10]:  # Focus on top 10
    county = row['county']
    precinct = row['precinct']
    voter_count = row['voter_count']
    
    print(f"\n{county} - Precinct '{precinct}' ({voter_count:,} voters)")
    
    # Extract numbers from precinct
    numbers = re.findall(r'\d+', precinct)
    if numbers:
        # Try to find similar precincts in reference data
        search_pattern = '%' + numbers[0] + '%'
        
        cursor.execute("""
            SELECT DISTINCT precinct, congressional_district
            FROM precinct_districts
            WHERE county = ?
            AND precinct LIKE ?
            LIMIT 5
        """, (county, search_pattern))
        
        matches = cursor.fetchall()
        if matches:
            print(f"  Potential matches in reference data:")
            for match in matches:
                print(f"    '{match['precinct']}' → District {match['congressional_district']}")
                
                # If there's only one match, suggest it
                if len(matches) == 1:
                    manual_mappings.append({
                        'county': county,
                        'precinct': precinct,
                        'ref_precinct': match['precinct'],
                        'district': match['congressional_district'],
                        'voters': voter_count
                    })
        else:
            print(f"  No similar precincts found in reference data")

# Apply manual mappings
if manual_mappings:
    print("\n3. APPLYING MANUAL MAPPINGS")
    print("-" * 80)
    
    total_fixed = 0
    
    for mapping in manual_mappings:
        print(f"\nMapping {mapping['county']} precinct '{mapping['precinct']}' to District {mapping['district']}")
        print(f"  (Based on reference precinct '{mapping['ref_precinct']}')")
        print(f"  Will fix {mapping['voters']:,} voters")
        
        # Update voter_elections
        district_code = f"TX-{mapping['district']}" if mapping['district'].isdigit() else mapping['district']
        
        cursor.execute("""
            UPDATE voter_elections
            SET congressional_district = ?
            WHERE election_date = ?
            AND precinct = ?
            AND vuid IN (
                SELECT ve.vuid FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE v.county = ?
                AND ve.election_date = ?
            )
        """, (district_code, ELECTION_DATE, mapping['precinct'], mapping['county'], ELECTION_DATE))
        
        fixed = cursor.rowcount
        total_fixed += fixed
        print(f"  ✓ Fixed {fixed:,} records")
    
    conn.commit()
    
    print(f"\nTotal records fixed: {total_fixed:,}")

# Check D15 status after improvements
print("\n4. D15 STATUS AFTER IMPROVEMENTS")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(DISTINCT vuid)
    FROM voter_elections
    WHERE election_date = ?
    AND party_voted = 'Democratic'
    AND congressional_district = 'TX-15'
""", (ELECTION_DATE,))

current_d15 = cursor.fetchone()[0]
official_d15 = 54573
accuracy = 100 * current_d15 / official_d15

print(f"Current D15 assignment:    {current_d15:>10,}")
print(f"Official D15 count:        {official_d15:>10,}")
print(f"Accuracy:                  {accuracy:>10.2f}%")

conn.close()
