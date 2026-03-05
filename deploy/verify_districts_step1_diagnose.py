#!/usr/bin/env python3
"""
STEP 1: DIAGNOSE - Identify all district assignment errors
Run this first to understand the scope of the problem.
"""

import sqlite3
import json
from collections import defaultdict

def main():
    print("=" * 80)
    print("DISTRICT ACCURACY DIAGNOSIS")
    print("=" * 80)
    
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    # Define what we KNOW is wrong
    KNOWN_WRONG_ASSIGNMENTS = {
        'TX-15': {
            'wrong_counties': ['Travis', 'Bexar', 'Dallas', 'Tarrant', 'Harris'],
            'correct_counties': ['Hidalgo', 'Starr', 'Brooks', 'Jim Hogg', 'Willacy', 'Kenedy']
        },
        # Add more as we discover them
    }
    
    print("\n" + "=" * 80)
    print("1. CONGRESSIONAL DISTRICTS - County Distribution")
    print("=" * 80)
    
    # Get all congressional district assignments by county
    cd_data = conn.execute('''
        SELECT congressional_district, county, COUNT(*) as voter_count
        FROM voters
        WHERE congressional_district IS NOT NULL AND congressional_district != ''
        GROUP BY congressional_district, county
        ORDER BY congressional_district, voter_count DESC
    ''').fetchall()
    
    # Organize by district
    districts = defaultdict(list)
    for row in cd_data:
        districts[row['congressional_district']].append({
            'county': row['county'],
            'voters': row['voter_count']
        })
    
    # Check each district
    errors_found = []
    
    for district in sorted(districts.keys()):
        counties = districts[district]
        total_voters = sum(c['voters'] for c in counties)
        
        print(f"\nTX-{district}: {total_voters:,} voters across {len(counties)} counties")
        
        # Check for known wrong assignments
        if f'TX-{district}' in KNOWN_WRONG_ASSIGNMENTS:
            wrong_counties = KNOWN_WRONG_ASSIGNMENTS[f'TX-{district}']['wrong_counties']
            correct_counties = KNOWN_WRONG_ASSIGNMENTS[f'TX-{district}']['correct_counties']
            
            for county_data in counties:
                county = county_data['county']
                voters = county_data['voters']
                
                if county in wrong_counties:
                    print(f"  ✗ {county}: {voters:,} voters (WRONG!)")
                    errors_found.append({
                        'district': district,
                        'county': county,
                        'voters': voters,
                        'error': 'wrong_county'
                    })
                elif county in correct_counties:
                    print(f"  ✓ {county}: {voters:,} voters")
                else:
                    print(f"  ? {county}: {voters:,} voters (needs verification)")
        else:
            # Just list top 5 counties for other districts
            for i, county_data in enumerate(counties[:5]):
                print(f"  - {county_data['county']}: {county_data['voters']:,} voters")
            if len(counties) > 5:
                print(f"  ... and {len(counties) - 5} more counties")
    
    print("\n" + "=" * 80)
    print("2. STATE HOUSE DISTRICTS - County Distribution")
    print("=" * 80)
    
    # Check state house districts
    sh_data = conn.execute('''
        SELECT state_house_district, county, COUNT(*) as voter_count
        FROM voters
        WHERE state_house_district IS NOT NULL AND state_house_district != ''
        GROUP BY state_house_district, county
        ORDER BY state_house_district, voter_count DESC
    ''').fetchall()
    
    sh_districts = defaultdict(list)
    for row in sh_data:
        sh_districts[row['state_house_district']].append({
            'county': row['county'],
            'voters': row['voter_count']
        })
    
    print(f"\nTotal State House Districts: {len(sh_districts)}")
    print("Sample districts:")
    for district in sorted(sh_districts.keys())[:5]:
        counties = sh_districts[district]
        total_voters = sum(c['voters'] for c in counties)
        print(f"  HD-{district}: {total_voters:,} voters across {len(counties)} counties")
    
    print("\n" + "=" * 80)
    print("3. COMMISSIONER DISTRICTS - County Distribution")
    print("=" * 80)
    
    # Check commissioner districts (should be county-specific)
    comm_data = conn.execute('''
        SELECT commissioner_district, county, COUNT(*) as voter_count
        FROM voters
        WHERE commissioner_district IS NOT NULL AND commissioner_district != ''
        GROUP BY commissioner_district, county
        ORDER BY commissioner_district, voter_count DESC
    ''').fetchall()
    
    comm_districts = defaultdict(list)
    for row in comm_data:
        comm_districts[row['commissioner_district']].append({
            'county': row['county'],
            'voters': row['voter_count']
        })
    
    # Commissioner districts should NEVER span multiple counties
    multi_county_comm = []
    for district, counties in comm_districts.items():
        if len(counties) > 1:
            multi_county_comm.append({
                'district': district,
                'counties': [c['county'] for c in counties],
                'voters': sum(c['voters'] for c in counties)
            })
    
    if multi_county_comm:
        print(f"\n✗ CRITICAL: {len(multi_county_comm)} commissioner districts span multiple counties!")
        print("  Commissioner districts MUST be within a single county.")
        for item in multi_county_comm[:10]:
            print(f"  - District {item['district']}: {', '.join(item['counties'])} ({item['voters']:,} voters)")
        errors_found.extend([{
            'district': item['district'],
            'counties': item['counties'],
            'voters': item['voters'],
            'error': 'multi_county_commissioner'
        } for item in multi_county_comm])
    else:
        print("\n✓ All commissioner districts are within single counties")
    
    print("\n" + "=" * 80)
    print("4. GEOCODED VOTERS - Coordinate Validation")
    print("=" * 80)
    
    # Check if geocoded voters have district assignments
    geocoded_stats = conn.execute('''
        SELECT 
            COUNT(*) as total_geocoded,
            COUNT(CASE WHEN congressional_district IS NOT NULL THEN 1 END) as with_cd,
            COUNT(CASE WHEN state_house_district IS NOT NULL THEN 1 END) as with_sh,
            COUNT(CASE WHEN commissioner_district IS NOT NULL THEN 1 END) as with_comm
        FROM voters
        WHERE geocoded = 1 AND lat IS NOT NULL AND lng IS NOT NULL
    ''').fetchone()
    
    print(f"\nGeocoded voters: {geocoded_stats['total_geocoded']:,}")
    print(f"  With Congressional District: {geocoded_stats['with_cd']:,} ({geocoded_stats['with_cd']/geocoded_stats['total_geocoded']*100:.1f}%)")
    print(f"  With State House District: {geocoded_stats['with_sh']:,} ({geocoded_stats['with_sh']/geocoded_stats['total_geocoded']*100:.1f}%)")
    print(f"  With Commissioner District: {geocoded_stats['with_comm']:,} ({geocoded_stats['with_comm']/geocoded_stats['total_geocoded']*100:.1f}%)")
    
    print("\n" + "=" * 80)
    print("5. PRECINCT DATA - Completeness Check")
    print("=" * 80)
    
    precinct_stats = conn.execute('''
        SELECT 
            county,
            COUNT(*) as total_voters,
            COUNT(CASE WHEN precinct IS NOT NULL AND precinct != '' THEN 1 END) as with_precinct,
            COUNT(DISTINCT precinct) as unique_precincts
        FROM voters
        GROUP BY county
        ORDER BY total_voters DESC
        LIMIT 10
    ''').fetchall()
    
    print("\nTop 10 counties by voter count:")
    for row in precinct_stats:
        pct = row['with_precinct'] / row['total_voters'] * 100 if row['total_voters'] > 0 else 0
        print(f"  {row['county']}: {row['total_voters']:,} voters, {row['with_precinct']:,} with precinct ({pct:.1f}%), {row['unique_precincts']} unique precincts")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    print(f"\n✗ Errors found: {len(errors_found)}")
    
    if errors_found:
        print("\nCritical issues:")
        wrong_county_voters = sum(e['voters'] for e in errors_found if e['error'] == 'wrong_county')
        if wrong_county_voters > 0:
            print(f"  - {wrong_county_voters:,} voters assigned to wrong counties")
        
        multi_county_comm_count = len([e for e in errors_found if e['error'] == 'multi_county_commissioner'])
        if multi_county_comm_count > 0:
            print(f"  - {multi_county_comm_count} commissioner districts span multiple counties")
    
    print("\n" + "=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print("\n1. Run: python3 verify_districts_step2_acquire.py")
    print("   Download official district boundaries")
    print("\n2. Run: python3 verify_districts_step3_validate.py")
    print("   Build validation tools")
    print("\n3. Run: python3 verify_districts_step4_rebuild.py")
    print("   Regenerate all district assignments")
    
    # Save errors to file for next steps
    if errors_found:
        with open('data/district_errors.json', 'w') as f:
            json.dump(errors_found, f, indent=2)
        print(f"\n✓ Saved {len(errors_found)} errors to data/district_errors.json")

if __name__ == '__main__':
    main()
