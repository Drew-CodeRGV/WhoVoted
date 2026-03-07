#!/usr/bin/env python3
"""
Normalize precinct/county formats and assign ALL districts to ALL voters.
This script ensures 100% district assignment coverage.
"""

import sqlite3
import re

def normalize_precinct(precinct):
    """Normalize precinct format for matching."""
    if not precinct or precinct == 'None':
        return None
    
    precinct = str(precinct).strip()
    
    # Remove "** " prefix if present
    precinct = precinct.replace('** ', '')
    
    # Pad to 4 digits if it's a number
    if precinct.isdigit():
        return precinct.zfill(4)
    
    # Handle mixed format like "0011" -> keep as is
    return precinct

def normalize_county(county):
    """Normalize county name for matching."""
    if not county:
        return None
    
    county = str(county).strip()
    
    # Remove asterisk and spaces
    county = county.replace(' *', '').replace('*', '').strip()
    
    return county

def create_normalized_lookup(db_path):
    """Create normalized lookup table with all variations."""
    print("Creating normalized lookup table...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create normalized lookup table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precinct_district_lookup_normalized (
            county_normalized TEXT NOT NULL,
            precinct_normalized TEXT NOT NULL,
            congressional_district TEXT,
            state_senate_district TEXT,
            state_house_district TEXT,
            PRIMARY KEY (county_normalized, precinct_normalized)
        )
    """)
    
    # Clear existing data
    cursor.execute("DELETE FROM precinct_district_lookup_normalized")
    
    # Get all lookup data
    cursor.execute("""
        SELECT county, precinct, congressional_district, state_senate_district, state_house_district
        FROM precinct_district_lookup
    """)
    
    normalized_count = 0
    for row in cursor.fetchall():
        county, precinct, cong, senate, house = row
        
        county_norm = normalize_county(county)
        precinct_norm = normalize_precinct(precinct)
        
        if county_norm and precinct_norm:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO precinct_district_lookup_normalized
                    (county_normalized, precinct_normalized, congressional_district, state_senate_district, state_house_district)
                    VALUES (?, ?, ?, ?, ?)
                """, (county_norm, precinct_norm, cong, senate, house))
                normalized_count += 1
            except Exception as e:
                print(f"  Warning: Could not insert {county_norm}/{precinct_norm}: {e}")
    
    conn.commit()
    
    # Create index
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_normalized_lookup 
        ON precinct_district_lookup_normalized(county_normalized, precinct_normalized)
    """)
    
    print(f"  ✓ Created normalized lookup with {normalized_count:,} entries")
    
    # Show sample
    cursor.execute("""
        SELECT county_normalized, precinct_normalized, congressional_district
        FROM precinct_district_lookup_normalized
        LIMIT 5
    """)
    print("\n  Sample normalized entries:")
    for row in cursor.fetchall():
        print(f"    {row[0]} / {row[1]} -> TX-{row[2]}")
    
    conn.close()

def assign_all_districts(db_path):
    """Assign all 3 district types to all voters using normalized matching."""
    print("\n" + "="*80)
    print("ASSIGNING ALL DISTRICTS TO ALL VOTERS")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check current state
    cursor.execute("SELECT COUNT(*) FROM voters")
    total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT 
            COUNT(congressional_district) as has_cong,
            COUNT(state_senate_district) as has_senate,
            COUNT(state_house_district) as has_house
        FROM voters
    """)
    before = cursor.fetchone()
    
    print(f"\nBefore assignment:")
    print(f"  Total voters: {total:,}")
    print(f"  Congressional: {before[0]:,} ({before[0]/total*100:.1f}%)")
    print(f"  State Senate: {before[1]:,} ({before[1]/total*100:.1f}%)")
    print(f"  State House: {before[2]:,} ({before[2]/total*100:.1f}%)")
    
    # Update using normalized matching
    print("\nUpdating districts using normalized matching...")
    
    # We'll do this in batches for better performance
    batch_size = 10000
    cursor.execute("SELECT COUNT(*) FROM voters WHERE county IS NOT NULL AND precinct IS NOT NULL")
    voters_with_precinct = cursor.fetchone()[0]
    
    print(f"  Processing {voters_with_precinct:,} voters with precinct data...")
    
    updated = 0
    for offset in range(0, voters_with_precinct, batch_size):
        cursor.execute("""
            SELECT vuid, county, precinct
            FROM voters
            WHERE county IS NOT NULL AND precinct IS NOT NULL
            LIMIT ? OFFSET ?
        """, (batch_size, offset))
        
        batch = cursor.fetchall()
        
        for vuid, county, precinct in batch:
            county_norm = normalize_county(county)
            precinct_norm = normalize_precinct(precinct)
            
            if county_norm and precinct_norm:
                # Look up districts
                cursor.execute("""
                    SELECT congressional_district, state_senate_district, state_house_district
                    FROM precinct_district_lookup_normalized
                    WHERE county_normalized = ? AND precinct_normalized = ?
                """, (county_norm, precinct_norm))
                
                result = cursor.fetchone()
                if result:
                    cong, senate, house = result
                    cursor.execute("""
                        UPDATE voters
                        SET congressional_district = ?,
                            state_senate_district = ?,
                            state_house_district = ?
                        WHERE vuid = ?
                    """, (cong, senate, house, vuid))
                    updated += 1
        
        if (offset + batch_size) % 100000 == 0:
            print(f"    Processed {offset + batch_size:,} voters...")
            conn.commit()
    
    conn.commit()
    print(f"  ✓ Updated {updated:,} voters")
    
    # Check final state
    cursor.execute("""
        SELECT 
            COUNT(congressional_district) as has_cong,
            COUNT(state_senate_district) as has_senate,
            COUNT(state_house_district) as has_house
        FROM voters
    """)
    after = cursor.fetchone()
    
    print(f"\nAfter assignment:")
    print(f"  Congressional: {after[0]:,} ({after[0]/total*100:.1f}%)")
    print(f"  State Senate: {after[1]:,} ({after[1]/total*100:.1f}%)")
    print(f"  State House: {after[2]:,} ({after[2]/total*100:.1f}%)")
    
    # Show improvement
    print(f"\nImprovement:")
    print(f"  Congressional: +{after[0]-before[0]:,} voters ({(after[0]-before[0])/total*100:.1f}%)")
    print(f"  State Senate: +{after[1]-before[1]:,} voters ({(after[1]-before[1])/total*100:.1f}%)")
    print(f"  State House: +{after[2]-before[2]:,} voters ({(after[2]-before[2])/total*100:.1f}%)")
    
    # Check for voters without districts
    cursor.execute("""
        SELECT COUNT(*)
        FROM voters
        WHERE congressional_district IS NULL
        OR state_senate_district IS NULL
        OR state_house_district IS NULL
    """)
    missing = cursor.fetchone()[0]
    
    if missing > 0:
        print(f"\n⚠ {missing:,} voters still missing district assignments")
        
        # Analyze why
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN county IS NULL THEN 1 ELSE 0 END) as no_county,
                SUM(CASE WHEN precinct IS NULL OR precinct = '' THEN 1 ELSE 0 END) as no_precinct,
                SUM(CASE WHEN county IS NOT NULL AND precinct IS NOT NULL AND precinct != '' THEN 1 ELSE 0 END) as has_both
            FROM voters
            WHERE congressional_district IS NULL
            OR state_senate_district IS NULL
            OR state_house_district IS NULL
        """)
        analysis = cursor.fetchone()
        print(f"  Missing county: {analysis[0]:,}")
        print(f"  Missing precinct: {analysis[1]:,}")
        print(f"  Has both but no match: {analysis[2]:,}")
    
    conn.close()

def verify_district_counts(db_path):
    """Verify district counts are reasonable."""
    print("\n" + "="*80)
    print("VERIFYING DISTRICT COUNTS")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Congressional districts
    cursor.execute("""
        SELECT congressional_district, COUNT(*) as voters
        FROM voters
        WHERE congressional_district IS NOT NULL
        GROUP BY congressional_district
        ORDER BY congressional_district
    """)
    cong_districts = cursor.fetchall()
    
    print(f"\nCongressional Districts: {len(cong_districts)} districts")
    print("  Top 5 by voter count:")
    for district, count in sorted(cong_districts, key=lambda x: x[1], reverse=True)[:5]:
        print(f"    TX-{district}: {count:,} voters")
    
    # State Senate districts
    cursor.execute("""
        SELECT state_senate_district, COUNT(*) as voters
        FROM voters
        WHERE state_senate_district IS NOT NULL
        GROUP BY state_senate_district
        ORDER BY state_senate_district
    """)
    senate_districts = cursor.fetchall()
    
    print(f"\nState Senate Districts: {len(senate_districts)} districts")
    if senate_districts:
        print("  Top 5 by voter count:")
        for district, count in sorted(senate_districts, key=lambda x: x[1], reverse=True)[:5]:
            print(f"    SD-{district}: {count:,} voters")
    
    # State House districts
    cursor.execute("""
        SELECT state_house_district, COUNT(*) as voters
        FROM voters
        WHERE state_house_district IS NOT NULL
        GROUP BY state_house_district
        ORDER BY state_house_district
    """)
    house_districts = cursor.fetchall()
    
    print(f"\nState House Districts: {len(house_districts)} districts")
    if house_districts:
        print("  Top 5 by voter count:")
        for district, count in sorted(house_districts, key=lambda x: x[1], reverse=True)[:5]:
            print(f"    HD-{district}: {count:,} voters")
    
    conn.close()

def main():
    db_path = "data/whovoted.db"
    
    print("="*80)
    print("NORMALIZE AND ASSIGN ALL DISTRICTS")
    print("="*80)
    print("\nThis will:")
    print("  1. Normalize precinct and county formats")
    print("  2. Assign all 3 district types to every voter")
    print("  3. Verify district counts")
    print("="*80)
    
    # Step 1: Create normalized lookup
    create_normalized_lookup(db_path)
    
    # Step 2: Assign all districts
    assign_all_districts(db_path)
    
    # Step 3: Verify
    verify_district_counts(db_path)
    
    print("\n" + "="*80)
    print("✓ COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
