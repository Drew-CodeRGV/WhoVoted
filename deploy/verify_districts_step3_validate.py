#!/usr/bin/env python3
"""
STEP 3: VALIDATE - Build tools to verify district assignments
Test point-in-polygon logic and validate sample voters.
"""

import sqlite3
import json
import sys
from shapely.geometry import shape, Point
from shapely.ops import unary_union

def load_districts(filepath, district_field):
    """Load district boundaries from GeoJSON."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    districts = {}
    for feature in data['features']:
        props = feature['properties']
        district_num = props.get(district_field, props.get('DISTRICT', props.get('CD')))
        
        if district_num:
            district_num = str(district_num).strip()
            geom = shape(feature['geometry'])
            
            if district_num in districts:
                # Merge if district has multiple polygons
                districts[district_num] = unary_union([districts[district_num], geom])
            else:
                districts[district_num] = geom
    
    return districts

def find_district(lat, lng, districts):
    """Find which district a point falls in."""
    point = Point(lng, lat)  # Note: shapely uses (x, y) = (lng, lat)
    
    for district_num, geom in districts.items():
        if geom.contains(point):
            return district_num
    
    return None

def main():
    print("=" * 80)
    print("VALIDATE DISTRICT ASSIGNMENT LOGIC")
    print("=" * 80)
    
    # Load district boundaries
    print("\n" + "=" * 80)
    print("1. LOADING DISTRICT BOUNDARIES")
    print("=" * 80)
    
    try:
        cd_districts = load_districts('data/tx_congressional_2023.geojson', 'DISTRICT')
        print(f"✓ Loaded {len(cd_districts)} Congressional Districts")
    except FileNotFoundError:
        print("✗ Congressional districts file not found")
        print("  Run: python3 verify_districts_step2_acquire.py")
        return
    except Exception as e:
        print(f"✗ Error loading congressional districts: {e}")
        return
    
    try:
        sh_districts = load_districts('data/tx_state_house_2023.geojson', 'DISTRICT')
        print(f"✓ Loaded {len(sh_districts)} State House Districts")
    except FileNotFoundError:
        print("✗ State House districts file not found")
        sh_districts = None
    except Exception as e:
        print(f"✗ Error loading state house districts: {e}")
        sh_districts = None
    
    # Connect to database
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    print("\n" + "=" * 80)
    print("2. VALIDATE SAMPLE VOTERS")
    print("=" * 80)
    
    # Get sample of geocoded voters from different counties
    samples = conn.execute('''
        SELECT vuid, firstname, lastname, address, city, county, 
               lat, lng, congressional_district, state_house_district
        FROM voters
        WHERE geocoded = 1 AND lat IS NOT NULL AND lng IS NOT NULL
        AND county IN ('Hidalgo', 'Travis', 'Bexar', 'Dallas')
        ORDER BY RANDOM()
        LIMIT 20
    ''').fetchall()
    
    print(f"\nTesting {len(samples)} random geocoded voters...")
    
    correct = 0
    incorrect = 0
    errors = []
    
    for voter in samples:
        lat = voter['lat']
        lng = voter['lng']
        current_cd = voter['congressional_district']
        
        # Find correct district
        correct_cd = find_district(lat, lng, cd_districts)
        
        if correct_cd:
            if current_cd == correct_cd:
                print(f"✓ {voter['firstname']} {voter['lastname']} ({voter['county']})")
                print(f"  Current: TX-{current_cd}, Correct: TX-{correct_cd}")
                correct += 1
            else:
                print(f"✗ {voter['firstname']} {voter['lastname']} ({voter['county']})")
                print(f"  Current: TX-{current_cd}, Should be: TX-{correct_cd}")
                print(f"  Address: {voter['address']}, {voter['city']}")
                print(f"  Coords: {lat}, {lng}")
                incorrect += 1
                errors.append({
                    'vuid': voter['vuid'],
                    'name': f"{voter['firstname']} {voter['lastname']}",
                    'county': voter['county'],
                    'current_cd': current_cd,
                    'correct_cd': correct_cd,
                    'lat': lat,
                    'lng': lng
                })
        else:
            print(f"? {voter['firstname']} {voter['lastname']} ({voter['county']})")
            print(f"  Could not determine district for coords: {lat}, {lng}")
    
    print(f"\nResults: {correct} correct, {incorrect} incorrect")
    
    if incorrect > 0:
        accuracy = correct / (correct + incorrect) * 100
        print(f"Accuracy: {accuracy:.1f}%")
        
        # Save errors
        with open('data/validation_errors.json', 'w') as f:
            json.dump(errors, f, indent=2)
        print(f"\n✓ Saved {len(errors)} validation errors to data/validation_errors.json")
    
    print("\n" + "=" * 80)
    print("3. CHECK KNOWN PROBLEM CASES")
    print("=" * 80)
    
    # Check Travis County voters assigned to TX-15
    travis_in_tx15 = conn.execute('''
        SELECT COUNT(*) as count
        FROM voters
        WHERE county = 'Travis' AND congressional_district = '15'
    ''').fetchone()
    
    if travis_in_tx15['count'] > 0:
        print(f"\n✗ CRITICAL: {travis_in_tx15['count']} Travis County voters assigned to TX-15")
        print("  This is IMPOSSIBLE - Travis County is not in TX-15")
        
        # Sample a few
        samples = conn.execute('''
            SELECT vuid, firstname, lastname, address, city, lat, lng
            FROM voters
            WHERE county = 'Travis' AND congressional_district = '15'
            LIMIT 5
        ''').fetchall()
        
        print("\n  Sample voters:")
        for v in samples:
            if v['lat'] and v['lng']:
                correct_cd = find_district(v['lat'], v['lng'], cd_districts)
                print(f"    {v['firstname']} {v['lastname']}")
                print(f"      Address: {v['address']}, {v['city']}")
                print(f"      Coords: {v['lat']}, {v['lng']}")
                print(f"      Should be in: TX-{correct_cd}")
            else:
                print(f"    {v['firstname']} {v['lastname']} - NO COORDINATES")
    else:
        print("\n✓ No Travis County voters in TX-15")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if incorrect > 0:
        print(f"\n✗ Found {incorrect} incorrect assignments in sample")
        print("  District assignment logic needs to be rebuilt")
        print("\nNext step: python3 verify_districts_step4_rebuild.py")
    else:
        print("\n✓ All sample voters have correct district assignments")
        print("  But we still need to check ALL voters")
        print("\nNext step: python3 verify_districts_step4_rebuild.py")

if __name__ == '__main__':
    try:
        from shapely.geometry import shape, Point
        from shapely.ops import unary_union
        main()
    except ImportError:
        print("✗ Error: shapely library not installed")
        print("\nInstall with: pip install shapely")
        sys.exit(1)
