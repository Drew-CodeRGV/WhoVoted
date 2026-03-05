#!/usr/bin/env python3
"""
STEP 2: Identify Counties in TX-15
Verify which counties are actually in TX-15 and flag any incorrect assignments.
"""

import sqlite3
import json
import sys

def main():
    print("=" * 80)
    print("STEP 2: IDENTIFY COUNTIES IN TX-15")
    print("=" * 80)
    
    # Official TX-15 counties
    CORRECT_TX15_COUNTIES = {
        'Hidalgo',    # Partial
        'Brooks',     # Full
        'Jim Hogg',   # Full
        'Starr',      # Full
        'Willacy',    # Partial
        'Kenedy'      # Full
    }
    
    WRONG_COUNTIES = {
        'Travis',     # This is in TX-21, TX-25, TX-35, TX-37
        'Bexar',      # This is in TX-20, TX-23, TX-28, TX-35
        'Dallas',     # This is in TX-24, TX-30, TX-32, TX-33
        # Add more as we find them
    }
    
    print("\n✓ CORRECT TX-15 Counties:")
    for county in sorted(CORRECT_TX15_COUNTIES):
        print(f"  - {county}")
    
    print("\n✗ WRONG Counties (should NOT be in TX-15):")
    for county in sorted(WRONG_COUNTIES):
        print(f"  - {county}")
    
    # Check database
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    print("\n" + "-" * 80)
    print("CHECKING DATABASE...")
    print("-" * 80)
    
    # Check voters table for congressional_district assignments
    print("\nVoters by County and Congressional District:")
    
    county_district_counts = conn.execute('''
        SELECT county, congressional_district, COUNT(*) as voter_count
        FROM voters
        WHERE congressional_district = '15'
        GROUP BY county, congressional_district
        ORDER BY voter_count DESC
    ''').fetchall()
    
    total_tx15_voters = 0
    wrong_county_voters = 0
    
    for row in county_district_counts:
        county = row['county']
        district = row['congressional_district']
        count = row['voter_count']
        total_tx15_voters += count
        
        if county in WRONG_COUNTIES:
            print(f"  ✗ {county}: {count:,} voters (WRONG - should NOT be in TX-15!)")
            wrong_county_voters += count
        elif county in CORRECT_TX15_COUNTIES:
            print(f"  ✓ {county}: {count:,} voters (correct)")
        else:
            print(f"  ? {county}: {count:,} voters (unknown - needs verification)")
    
    print(f"\nTotal TX-15 voters in database: {total_tx15_voters:,}")
    print(f"Voters in WRONG counties: {wrong_county_voters:,} ({wrong_county_voters/total_tx15_voters*100:.1f}%)")
    
    # Check if we have precinct data
    print("\n" + "-" * 80)
    print("PRECINCT DATA CHECK")
    print("-" * 80)
    
    precinct_check = conn.execute('''
        SELECT COUNT(DISTINCT precinct) as precinct_count,
               COUNT(*) as voter_count
        FROM voters
        WHERE congressional_district = '15' AND precinct IS NOT NULL AND precinct != ''
    ''').fetchone()
    
    print(f"Voters with precinct data: {precinct_check['voter_count']:,}")
    print(f"Unique precincts: {precinct_check['precinct_count']:,}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("FINDINGS:")
    print("=" * 80)
    
    if wrong_county_voters > 0:
        print(f"✗ CRITICAL: {wrong_county_voters:,} voters are assigned to TX-15 from wrong counties!")
        print("  This explains why the district numbers are way off.")
        print("\n  ACTION REQUIRED: Re-assign these voters to correct districts")
    else:
        print("✓ All TX-15 voters are from correct counties")
    
    print("\n" + "=" * 80)
    print("NEXT STEP: Run verify_tx15_step3_precincts.py")
    print("=" * 80)

if __name__ == '__main__':
    main()
