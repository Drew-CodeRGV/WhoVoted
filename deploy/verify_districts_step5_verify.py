#!/usr/bin/env python3
"""
STEP 5: VERIFY - Confirm all district assignments are now correct
Run comprehensive checks to ensure the rebuild was successful.
"""

import sqlite3
import json

def main():
    print("=" * 80)
    print("VERIFY DISTRICT ASSIGNMENTS")
    print("=" * 80)
    
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    print("\n" + "=" * 80)
    print("1. CHECK KNOWN PROBLEM CASES")
    print("=" * 80)
    
    # Travis County in TX-15 (should be ZERO)
    travis_tx15 = conn.execute('''
        SELECT COUNT(*) as count
        FROM voters
        WHERE county = 'Travis' AND congressional_district = '15'
    ''').fetchone()['count']
    
    if travis_tx15 == 0:
        print("✓ Travis County voters NOT in TX-15 (correct)")
    else:
        print(f"✗ STILL BROKEN: {travis_tx15} Travis County voters in TX-15")
    
    # Check other wrong counties in TX-15
    wrong_counties = ['Bexar', 'Dallas', 'Tarrant', 'Harris']
    for county in wrong_counties:
        count = conn.execute('''
            SELECT COUNT(*) as count
            FROM voters
            WHERE county = ? AND congressional_district = '15'
        ''', (county,)).fetchone()['count']
        
        if count == 0:
            print(f"✓ {county} County voters NOT in TX-15 (correct)")
        else:
            print(f"✗ {count} {county} County voters still in TX-15")
    
    print("\n" + "=" * 80)
    print("2. TX-15 COMPOSITION CHECK")
    print("=" * 80)
    
    # TX-15 should only have these counties
    correct_tx15_counties = ['Hidalgo', 'Starr', 'Brooks', 'Jim Hogg', 'Willacy', 'Kenedy']
    
    tx15_counties = conn.execute('''
        SELECT county, COUNT(*) as voter_count
        FROM voters
        WHERE congressional_district = '15'
        GROUP BY county
        ORDER BY voter_count DESC
    ''').fetchall()
    
    print("\nTX-15 County Composition:")
    total_tx15 = 0
    all_correct = True
    
    for row in tx15_counties:
        county = row['county']
        count = row['voter_count']
        total_tx15 += count
        
        if county in correct_tx15_counties:
            print(f"  ✓ {county}: {count:,} voters")
        else:
            print(f"  ✗ {county}: {count:,} voters (SHOULD NOT BE HERE)")
            all_correct = False
    
    print(f"\nTotal TX-15 voters: {total_tx15:,}")
    
    if all_correct:
        print("✓ TX-15 composition is correct")
    else:
        print("✗ TX-15 still has voters from wrong counties")
    
    print("\n" + "=" * 80)
    print("3. COMMISSIONER DISTRICTS CHECK")
    print("=" * 80)
    
    # Commissioner districts should NEVER span multiple counties
    multi_county = conn.execute('''
        SELECT commissioner_district, COUNT(DISTINCT county) as county_count
        FROM voters
        WHERE commissioner_district IS NOT NULL AND commissioner_district != ''
        GROUP BY commissioner_district
        HAVING COUNT(DISTINCT county) > 1
    ''').fetchall()
    
    if len(multi_county) == 0:
        print("✓ No commissioner districts span multiple counties")
    else:
        print(f"✗ {len(multi_county)} commissioner districts span multiple counties:")
        for row in multi_county[:10]:
            print(f"  - District {row['commissioner_district']}: {row['county_count']} counties")
    
    print("\n" + "=" * 80)
    print("4. COVERAGE CHECK")
    print("=" * 80)
    
    # Check what percentage of geocoded voters have district assignments
    coverage = conn.execute('''
        SELECT 
            COUNT(*) as total_geocoded,
            COUNT(CASE WHEN congressional_district IS NOT NULL THEN 1 END) as with_cd,
            COUNT(CASE WHEN state_house_district IS NOT NULL THEN 1 END) as with_sh
        FROM voters
        WHERE geocoded = 1 AND lat IS NOT NULL AND lng IS NOT NULL
    ''').fetchone()
    
    cd_pct = coverage['with_cd'] / coverage['total_geocoded'] * 100
    sh_pct = coverage['with_sh'] / coverage['total_geocoded'] * 100
    
    print(f"\nGeocoded voters: {coverage['total_geocoded']:,}")
    print(f"  With Congressional District: {coverage['with_cd']:,} ({cd_pct:.1f}%)")
    print(f"  With State House District: {coverage['with_sh']:,} ({sh_pct:.1f}%)")
    
    if cd_pct > 95:
        print("✓ Good congressional district coverage")
    else:
        print(f"⚠️  Low congressional district coverage: {cd_pct:.1f}%")
    
    print("\n" + "=" * 80)
    print("5. DISTRICT DISTRIBUTION")
    print("=" * 80)
    
    # Show top 10 congressional districts by voter count
    top_districts = conn.execute('''
        SELECT congressional_district, COUNT(*) as voter_count
        FROM voters
        WHERE congressional_district IS NOT NULL
        GROUP BY congressional_district
        ORDER BY voter_count DESC
        LIMIT 10
    ''').fetchall()
    
    print("\nTop 10 Congressional Districts by voter count:")
    for row in top_districts:
        print(f"  TX-{row['congressional_district']}: {row['voter_count']:,} voters")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if travis_tx15 == 0 and all_correct and len(multi_county) == 0:
        print("\n✓ ALL CHECKS PASSED")
        print("  District assignments are now correct")
        print("\nNext step: python3 verify_districts_step6_prevent.py")
    else:
        print("\n✗ SOME CHECKS FAILED")
        print("  Review the errors above and re-run step 4 if needed")

if __name__ == '__main__':
    main()
