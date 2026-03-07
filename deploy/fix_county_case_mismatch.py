#!/usr/bin/env python3
"""
Fix county name case mismatches between database and lookup table.
Makes county matching case-insensitive and handles spaces.
"""

import sqlite3

def normalize_county(county):
    """Normalize county name for matching."""
    if not county:
        return None
    # Remove spaces, convert to lowercase for matching
    return county.replace(' ', '').lower()

def main():
    print("="*80)
    print("FIXING COUNTY NAME CASE MISMATCHES")
    print("="*80)
    
    conn = sqlite3.connect('data/whovoted.db')
    cursor = conn.cursor()
    
    # Add normalized column to lookup table
    print("\nStep 1: Adding normalized county column to lookup table...")
    cursor.execute("""
        ALTER TABLE county_district_lookup 
        ADD COLUMN county_normalized TEXT
    """)
    
    cursor.execute("""
        UPDATE county_district_lookup
        SET county_normalized = LOWER(REPLACE(county, ' ', ''))
    """)
    
    cursor.execute("""
        CREATE INDEX idx_county_normalized ON county_district_lookup(county_normalized)
    """)
    
    conn.commit()
    print("  ✓ Normalized column created and indexed")
    
    # Now update voters using normalized matching
    print("\nStep 2: Assigning districts using normalized county names...")
    
    cursor.execute("""
        UPDATE voters
        SET 
            congressional_district = COALESCE(
                congressional_district,
                (SELECT congressional_district 
                 FROM county_district_lookup 
                 WHERE county_normalized = LOWER(REPLACE(voters.county, ' ', '')))
            ),
            state_senate_district = COALESCE(
                state_senate_district,
                (SELECT state_senate_district 
                 FROM county_district_lookup 
                 WHERE county_normalized = LOWER(REPLACE(voters.county, ' ', '')))
            ),
            state_house_district = COALESCE(
                state_house_district,
                (SELECT state_house_district 
                 FROM county_district_lookup 
                 WHERE county_normalized = LOWER(REPLACE(voters.county, ' ', '')))
            )
        WHERE county IS NOT NULL
        AND (congressional_district IS NULL
             OR state_senate_district IS NULL
             OR state_house_district IS NULL)
    """)
    
    conn.commit()
    print(f"  ✓ Updated {cursor.rowcount} voters")
    
    # Check results
    print("\n" + "="*80)
    print("FINAL RESULTS")
    print("="*80)
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            COUNT(congressional_district) as has_cong,
            COUNT(state_senate_district) as has_senate,
            COUNT(state_house_district) as has_house,
            SUM(CASE WHEN congressional_district IS NOT NULL 
                     AND state_senate_district IS NOT NULL 
                     AND state_house_district IS NOT NULL THEN 1 ELSE 0 END) as has_all
        FROM voters
    """)
    result = cursor.fetchone()
    
    print(f"\nTotal voters: {result[0]:,}")
    print(f"Congressional District: {result[1]:,} ({result[1]/result[0]*100:.2f}%)")
    print(f"State Senate District: {result[2]:,} ({result[2]/result[0]*100:.2f}%)")
    print(f"State House District: {result[3]:,} ({result[3]/result[0]*100:.2f}%)")
    print(f"ALL 3 Districts: {result[4]:,} ({result[4]/result[0]*100:.2f}%)")
    
    # Check remaining unassigned
    cursor.execute("""
        SELECT COUNT(*) 
        FROM voters
        WHERE congressional_district IS NULL
           OR state_senate_district IS NULL
           OR state_house_district IS NULL
    """)
    remaining = cursor.fetchone()[0]
    
    if remaining > 0:
        print(f"\n⚠ Still {remaining:,} voters without all districts")
        
        cursor.execute("""
            SELECT county, COUNT(*) as count
            FROM voters
            WHERE congressional_district IS NULL
               OR state_senate_district IS NULL
               OR state_house_district IS NULL
            GROUP BY county
            ORDER BY count DESC
            LIMIT 10
        """)
        
        print("\nTop counties with unassigned voters:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]:,} voters")
    else:
        print("\n✓ ALL VOTERS HAVE ALL DISTRICTS!")
    
    conn.close()

if __name__ == '__main__':
    main()
