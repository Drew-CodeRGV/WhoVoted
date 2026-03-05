#!/usr/bin/env python3
"""
FIX ALL DISTRICTS - Using Existing Boundary Files
Preserves all your hard work on boundary files.
Only regenerates voter assignments based on coordinates.
"""

import sqlite3
import json
import sys
import os
from datetime import datetime
from shapely.geometry import shape, Point
from shapely.ops import unary_union

def load_districts_from_file(filepath, district_field='district_id'):
    """Load district boundaries from GeoJSON."""
    print(f"Loading {filepath}...")
    
    if not os.path.exists(filepath):
        print(f"  ✗ File not found")
        return None
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    districts = {}
    features = data.get('features', [])
    
    for feature in features:
        props = feature['properties']
        
        # Try multiple field names for district ID
        district_id = None
        for field in [district_field, 'district_id', 'DISTRICT', 'District', 'CD', 'NAME', 'BASENAME']:
            if field in props:
                district_id = str(props[field]).strip()
                break
        
        if not district_id:
            continue
        
        geom = shape(feature['geometry'])
        
        if district_id in districts:
            districts[district_id] = unary_union([districts[district_id], geom])
        else:
            districts[district_id] = geom
    
    print(f"  ✓ Loaded {len(districts)} districts")
    return districts

def find_district(lat, lng, districts):
    """Find which district a point falls in."""
    if not lat or not lng or not districts:
        return None
    
    point = Point(lng, lat)
    
    for district_id, geom in districts.items():
        try:
            if geom.contains(point):
                return district_id
        except:
            continue
    
    return None

def main():
    print("=" * 80)
    print("FIX ALL DISTRICT ASSIGNMENTS - PRESERVE BOUNDARY FILES")
    print("=" * 80)
    
    print("\n✓ Using existing boundary files (your hard work is preserved)")
    print("✓ Only regenerating voter assignments based on coordinates")
    
    print("\nDo you want to proceed? (yes/no): ", end='')
    response = input().strip().lower()
    if response != 'yes':
        print("Aborted.")
        return
    
    # Load all district boundary files
    print("\n" + "=" * 80)
    print("LOADING DISTRICT BOUNDARIES")
    print("=" * 80)
    
    # Congressional districts
    cd_districts = None
    cd_file = 'public/data/districts.json'
    if os.path.exists(cd_file):
        with open(cd_file, 'r') as f:
            data = json.load(f)
        cd_features = [f for f in data['features'] if f['properties']['district_type'] == 'congressional']
        if cd_features:
            cd_districts = {}
            for f in cd_features:
                dist_id = f['properties']['district_id']
                # Extract just the number (TX-15 -> 15)
                dist_num = dist_id.split('-')[-1]
                cd_districts[dist_num] = shape(f['geometry'])
            print(f"✓ Congressional: {len(cd_districts)} districts from {cd_file}")
    
    # State House districts
    sh_districts = None
    if os.path.exists(cd_file):
        with open(cd_file, 'r') as f:
            data = json.load(f)
        sh_features = [f for f in data['features'] if f['properties']['district_type'] == 'state_house']
        if sh_features:
            sh_districts = {}
            for f in sh_features:
                dist_id = f['properties']['district_id']
                # Extract just the number (HD-35 -> 35)
                dist_num = dist_id.split('-')[-1]
                sh_districts[dist_num] = shape(f['geometry'])
            print(f"✓ State House: {len(sh_districts)} districts from {cd_file}")
    
    # Commissioner districts (Hidalgo County)
    comm_districts = None
    comm_file = 'public/data/commissioner_precincts_hidalgo.json'
    if os.path.exists(comm_file):
        with open(comm_file, 'r') as f:
            data = json.load(f)
        comm_features = data.get('features', [])
        if comm_features:
            comm_districts = {}
            for f in comm_features:
                props = f['properties']
                # Try to find district number
                dist_num = None
                for field in ['district', 'DISTRICT', 'District', 'PRECINCT', 'Precinct', 'NAME', 'name']:
                    if field in props:
                        val = str(props[field]).strip()
                        # Extract number from strings like "Pct-1", "District 1", "1", etc.
                        import re
                        match = re.search(r'\d+', val)
                        if match:
                            dist_num = match.group()
                            break
                
                if dist_num:
                    # Prefix with county to avoid conflicts
                    dist_id = f"Hidalgo-{dist_num}"
                    comm_districts[dist_id] = shape(f['geometry'])
            
            print(f"✓ Commissioner (Hidalgo): {len(comm_districts)} districts from {comm_file}")
    
    if not cd_districts and not sh_districts and not comm_districts:
        print("\n✗ No district boundary files found!")
        print("  Expected files:")
        print(f"    - {cd_file}")
        print(f"    - {comm_file}")
        return
    
    # Connect to database
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    # Backup
    print("\n" + "=" * 80)
    print("CREATING BACKUP")
    print("=" * 80)
    
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
    
    # Get geocoded voters
    print("\n" + "=" * 80)
    print("PROCESSING GEOCODED VOTERS")
    print("=" * 80)
    
    voters = conn.execute('''
        SELECT vuid, lat, lng, county,
               congressional_district as old_cd,
               state_house_district as old_sh,
               commissioner_district as old_comm
        FROM voters
        WHERE geocoded = 1 AND lat IS NOT NULL AND lng IS NOT NULL
    ''').fetchall()
    
    print(f"\nFound {len(voters):,} geocoded voters")
    
    # Process each district type
    batch_size = 1000
    
    # Congressional Districts
    if cd_districts:
        print("\n" + "-" * 80)
        print("CONGRESSIONAL DISTRICTS")
        print("-" * 80)
        
        updated = 0
        unchanged = 0
        not_found = 0
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
            
            if len(updates) >= batch_size:
                conn.executemany(
                    'UPDATE voters SET congressional_district = ? WHERE vuid = ?',
                    updates
                )
                conn.commit()
                updates = []
        
        if updates:
            conn.executemany(
                'UPDATE voters SET congressional_district = ? WHERE vuid = ?',
                updates
            )
            conn.commit()
        
        print(f"\nResults:")
        print(f"  Updated: {updated:,}")
        print(f"  Unchanged: {unchanged:,}")
        print(f"  Not found: {not_found:,}")
    
    # State House Districts
    if sh_districts:
        print("\n" + "-" * 80)
        print("STATE HOUSE DISTRICTS")
        print("-" * 80)
        
        updated = 0
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
        
        print(f"\nResults:")
        print(f"  Updated: {updated:,}")
        print(f"  Not found: {not_found:,}")
    
    # Commissioner Districts (Hidalgo only)
    if comm_districts:
        print("\n" + "-" * 80)
        print("COMMISSIONER DISTRICTS (Hidalgo County)")
        print("-" * 80)
        
        # Only process Hidalgo County voters
        hidalgo_voters = [v for v in voters if v['county'] == 'Hidalgo']
        print(f"Processing {len(hidalgo_voters):,} Hidalgo County voters")
        
        updated = 0
        not_found = 0
        updates = []
        
        for i, voter in enumerate(hidalgo_voters):
            if i % 5000 == 0 and i > 0:
                print(f"  Processed {i:,} / {len(hidalgo_voters):,} ({i/len(hidalgo_voters)*100:.1f}%)")
            
            new_comm = find_district(voter['lat'], voter['lng'], comm_districts)
            
            if new_comm:
                # Strip county prefix for storage (Hidalgo-1 -> 1)
                new_comm_num = new_comm.split('-')[-1]
                updates.append((new_comm_num, voter['vuid']))
                updated += 1
            else:
                not_found += 1
            
            if len(updates) >= batch_size:
                conn.executemany(
                    'UPDATE voters SET commissioner_district = ? WHERE vuid = ?',
                    updates
                )
                conn.commit()
                updates = []
        
        if updates:
            conn.executemany(
                'UPDATE voters SET commissioner_district = ? WHERE vuid = ?',
                updates
            )
            conn.commit()
        
        print(f"\nResults:")
        print(f"  Updated: {updated:,}")
        print(f"  Not found: {not_found:,}")
    
    conn.close()
    
    # Verification
    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)
    
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    # Check TX-15
    travis_tx15 = conn.execute('''
        SELECT COUNT(*) as count
        FROM voters
        WHERE county = 'Travis' AND congressional_district = '15'
    ''').fetchone()['count']
    
    if travis_tx15 == 0:
        print("✓ Travis County voters NOT in TX-15 (correct)")
    else:
        print(f"✗ Still have {travis_tx15} Travis County voters in TX-15")
    
    # Check commissioner districts
    multi_county_comm = conn.execute('''
        SELECT commissioner_district, COUNT(DISTINCT county) as county_count
        FROM voters
        WHERE commissioner_district IS NOT NULL AND commissioner_district != ''
        GROUP BY commissioner_district
        HAVING COUNT(DISTINCT county) > 1
    ''').fetchall()
    
    if len(multi_county_comm) == 0:
        print("✓ No commissioner districts span multiple counties")
    else:
        print(f"✗ {len(multi_county_comm)} commissioner districts span multiple counties")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"\n✓ All district assignments rebuilt")
    print(f"✓ Backup saved to: {backup_table}")
    print("\nNext: Regenerate cached reports")
    print("  python3 deploy/regenerate_district_cache_complete.py")

if __name__ == '__main__':
    try:
        from shapely.geometry import shape, Point
        from shapely.ops import unary_union
        main()
    except ImportError:
        print("✗ Error: shapely library not installed")
        print("\nInstall with: pip install shapely")
        sys.exit(1)
