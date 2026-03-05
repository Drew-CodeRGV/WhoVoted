#!/usr/bin/env python3
"""
STEP 4: REBUILD - Regenerate ALL district assignments from scratch
This will fix all incorrect assignments using authoritative boundaries.
"""

import sqlite3
import json
import sys
from datetime import datetime
from shapely.geometry import shape, Point
from shapely.ops import unary_union

def load_districts(filepath, district_field):
    """Load district boundaries from GeoJSON."""
    print(f"Loading {filepath}...")
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
                districts[district_num] = unary_union([districts[district_num], geom])
            else:
                districts[district_num] = geom
    
    print(f"  Loaded {len(districts)} districts")
    return districts

def find_district(lat, lng, districts):
    """Find which district a point falls in."""
    if not lat or not lng:
        return None
    
    point = Point(lng, lat)
    
    for district_num, geom in districts.items():
        try:
            if geom.contains(point):
                return district_num
        except Exception as e:
            continue
    
    return None

def main():
    print("=" * 80)
    print("REBUILD ALL DISTRICT ASSIGNMENTS")
    print("=" * 80)
    
    # Confirm before proceeding
    print("\n⚠️  WARNING: This will UPDATE all district assignments in the database")
    print("   This operation will modify the 'voters' table")
    print("\nDo you want to proceed? (yes/no): ", end='')
    
    response = input().strip().lower()
    if response != 'yes':
        print("Aborted.")
        return
    
    # Load district boundaries
    print("\n" + "=" * 80)
    print("1. LOADING DISTRICT BOUNDARIES")
    print("=" * 80)
    
    try:
        cd_districts = load_districts('data/tx_congressional_2023.geojson', 'DISTRICT')
    except Exception as e:
        print(f"✗ Error loading congressional districts: {e}")
        return
    
    try:
        sh_districts = load_districts('data/tx_state_house_2023.geojson', 'DISTRICT')
    except Exception as e:
        print(f"⚠️  Could not load state house districts: {e}")
        sh_districts = None
    
    # Connect to database
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    print("\n" + "=" * 80)
    print("2. BACKUP CURRENT ASSIGNMENTS")
    print("=" * 80)
    
    # Save current assignments to backup table
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_table = f'voters_districts_backup_{timestamp}'
    
    conn.execute(f'''
        CREATE TABLE {backup_table} AS
        SELECT vuid, congressional_district, state_house_district, commissioner_district
        FROM voters
    ''')
    conn.commit()
    
    backup_count = conn.execute(f'SELECT COUNT(*) as count FROM {backup_table}').fetchone()['count']
    print(f"✓ Backed up {backup_count:,} voter district assignments to {backup_table}")
    
    print("\n" + "=" * 80)
    print("3. REGENERATE CONGRESSIONAL DISTRICTS")
    print("=" * 80)
    
    # Get all geocoded voters
    voters = conn.execute('''
        SELECT vuid, lat, lng, congressional_district as old_cd
        FROM voters
        WHERE geocoded = 1 AND lat IS NOT NULL AND lng IS NOT NULL
    ''').fetchall()
    
    print(f"\nProcessing {len(voters):,} geocoded voters...")
    
    updated = 0
    unchanged = 0
    not_found = 0
    
    batch_size = 1000
    updates = []
    
    for i, voter in enumerate(voters):
        if i % 10000 == 0 and i > 0:
            print(f"  Processed {i:,} / {len(voters):,} ({i/len(voters)*100:.1f}%)")
        
        new_cd = find_district(voter['lat'], voter['lng'], cd_districts)
        
        if new_cd:
            if new_cd != voter['old_cd']:
                updates.append((new_cd, voter['vuid']))
                updated += 1
            else:
                unchanged += 1
        else:
            not_found += 1
        
        # Batch update
        if len(updates) >= batch_size:
            conn.executemany(
                'UPDATE voters SET congressional_district = ? WHERE vuid = ?',
                updates
            )
            conn.commit()
            updates = []
    
    # Final batch
    if updates:
        conn.executemany(
            'UPDATE voters SET congressional_district = ? WHERE vuid = ?',
            updates
        )
        conn.commit()
    
    print(f"\nCongressional Districts:")
    print(f"  Updated: {updated:,}")
    print(f"  Unchanged: {unchanged:,}")
    print(f"  Not found: {not_found:,}")
    
    if sh_districts:
        print("\n" + "=" * 80)
        print("4. REGENERATE STATE HOUSE DISTRICTS")
        print("=" * 80)
        
        updated = 0
        unchanged = 0
        not_found = 0
        updates = []
        
        for i, voter in enumerate(voters):
            if i % 10000 == 0 and i > 0:
                print(f"  Processed {i:,} / {len(voters):,} ({i/len(voters)*100:.1f}%)")
            
            new_sh = find_district(voter['lat'], voter['lng'], sh_districts)
            
            if new_sh:
                updates.append((new_sh, voter['vuid']))
                updated += 1
            else:
                not_found += 1
            
            if len(updates) >= batch_size:
                conn.executemany(
                    'UPDATE voters SET state_house_district = ? WHERE vuid = ?',
                    updates
                )
                conn.commit()
                updates = []
        
        if updates:
            conn.executemany(
                'UPDATE voters SET state_house_district = ? WHERE vuid = ?',
                updates
            )
            conn.commit()
        
        print(f"\nState House Districts:")
        print(f"  Updated: {updated:,}")
        print(f"  Not found: {not_found:,}")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("5. REGENERATE CACHED REPORTS")
    print("=" * 80)
    
    print("\nCached district reports need to be regenerated.")
    print("Run: python3 deploy/regenerate_district_cache_complete.py")
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    
    print(f"\n✓ District assignments rebuilt successfully")
    print(f"✓ Backup saved to: {backup_table}")
    print("\nNext step: python3 verify_districts_step5_verify.py")

if __name__ == '__main__':
    try:
        from shapely.geometry import shape, Point
        from shapely.ops import unary_union
        main()
    except ImportError:
        print("✗ Error: shapely library not installed")
        print("\nInstall with: pip install shapely")
        sys.exit(1)
