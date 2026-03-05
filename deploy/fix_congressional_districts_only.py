#!/usr/bin/env python3
"""
SIMPLIFIED FIX: Only fix Congressional Districts
Preserves commissioner districts (D15 work).
Downloads PlanC2333 from Texas Legislature and rebuilds assignments.
"""

import sqlite3
import json
import sys
import os
import tempfile
import urllib.request
import zipfile
from datetime import datetime

def download_planc2333():
    """Download PlanC2333 congressional districts from Texas Legislature."""
    print("Downloading PlanC2333 congressional districts from Texas Legislature...")
    
    url = 'https://data.capitol.texas.gov/dataset/748c952b-e926-4f44-8d01-a738884b3ec8/resource/5712ebe1-d777-4d4a-b836-0534e17bca01/download/planc2333.zip'
    
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, 'planc2333.zip')
        
        print(f"  Downloading from: {url}")
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                with open(zip_path, 'wb') as f:
                    f.write(resp.read())
        except Exception as e:
            print(f"✗ Download failed: {e}")
            return None
        
        print(f"  Extracting...")
        with zipfile.ZipFile(zip_path, 'r') as z:
            z.extractall(tmpdir)
        
        # Find .shp file
        shp_path = None
        for root, dirs, files in os.walk(tmpdir):
            for f in files:
                if f.lower().endswith('.shp'):
                    shp_path = os.path.join(root, f)
                    break
            if shp_path:
                break
        
        if not shp_path:
            print("✗ Could not find .shp file in download")
            return None
        
        print(f"  Found shapefile: {os.path.basename(shp_path)}")
        
        # Convert to GeoJSON using shapely
        try:
            import shapefile
            from shapely.geometry import shape as shapely_shape, mapping
        except ImportError:
            print("✗ Missing required libraries")
            print("  Install with: pip install pyshp shapely")
            return None
        
        sf = shapefile.Reader(shp_path)
        
        features = []
        for sr in sf.shapeRecords():
            geom = sr.shape.__geo_interface__
            props = {}
            for i, field in enumerate(sf.fields[1:]):
                props[field[0]] = sr.record[i]
            
            # Extract district number
            dist_num = None
            for key in ['DISTRICT', 'District', 'CD', 'CONG_DIST']:
                val = props.get(key)
                if val is not None:
                    val_str = str(val).strip().lstrip('0')
                    if val_str.isdigit():
                        dist_num = val_str
                        break
            
            if dist_num:
                features.append({
                    'type': 'Feature',
                    'geometry': geom,
                    'properties': {'DISTRICT': dist_num}
                })
        
        geojson = {
            'type': 'FeatureCollection',
            'features': features
        }
        
        # Save to data directory
        output_path = 'data/tx_congressional_2023.geojson'
        with open(output_path, 'w') as f:
            json.dump(geojson, f)
        
        print(f"✓ Saved {len(features)} congressional districts to {output_path}")
        return output_path

def load_districts(filepath):
    """Load district boundaries from GeoJSON."""
    try:
        from shapely.geometry import shape
        from shapely.ops import unary_union
    except ImportError:
        print("✗ shapely not installed")
        print("  Install with: pip install shapely")
        sys.exit(1)
    
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    districts = {}
    for feature in data['features']:
        props = feature['properties']
        district_num = props.get('DISTRICT', props.get('District', props.get('CD')))
        
        if district_num:
            district_num = str(district_num).strip()
            geom = shape(feature['geometry'])
            
            if district_num in districts:
                districts[district_num] = unary_union([districts[district_num], geom])
            else:
                districts[district_num] = geom
    
    return districts

def find_district(lat, lng, districts):
    """Find which district a point falls in."""
    if not lat or not lng:
        return None
    
    try:
        from shapely.geometry import Point
    except ImportError:
        return None
    
    point = Point(lng, lat)
    
    for district_num, geom in districts.items():
        try:
            if geom.contains(point):
                return district_num
        except:
            continue
    
    return None

def main():
    print("=" * 80)
    print("FIX CONGRESSIONAL DISTRICTS ONLY")
    print("=" * 80)
    
    print("\n✓ Commissioner districts will NOT be touched (preserving D15 work)")
    print("✓ State House districts will NOT be touched")
    print("✓ Only Congressional districts will be rebuilt")
    
    print("\nDo you want to proceed? (yes/no): ", end='')
    response = input().strip().lower()
    if response != 'yes':
        print("Aborted.")
        return
    
    # Check if we have the district file
    geojson_path = 'data/tx_congressional_2023.geojson'
    if not os.path.exists(geojson_path):
        print(f"\n{geojson_path} not found. Downloading...")
        geojson_path = download_planc2333()
        if not geojson_path:
            print("✗ Failed to download district boundaries")
            return
    else:
        print(f"\n✓ Using existing {geojson_path}")
    
    # Load districts
    print("\nLoading congressional district boundaries...")
    cd_districts = load_districts(geojson_path)
    print(f"✓ Loaded {len(cd_districts)} congressional districts")
    
    # Connect to database
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    # Backup
    print("\nCreating backup...")
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_table = f'voters_cd_backup_{timestamp}'
    
    conn.execute(f'''
        CREATE TABLE {backup_table} AS
        SELECT vuid, congressional_district
        FROM voters
    ''')
    conn.commit()
    
    backup_count = conn.execute(f'SELECT COUNT(*) as count FROM {backup_table}').fetchone()['count']
    print(f"✓ Backed up {backup_count:,} congressional district assignments to {backup_table}")
    
    # Get geocoded voters
    print("\nProcessing geocoded voters...")
    voters = conn.execute('''
        SELECT vuid, lat, lng, congressional_district as old_cd
        FROM voters
        WHERE geocoded = 1 AND lat IS NOT NULL AND lng IS NOT NULL
    ''').fetchall()
    
    print(f"Found {len(voters):,} geocoded voters")
    
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
    
    print(f"\nResults:")
    print(f"  Updated: {updated:,}")
    print(f"  Unchanged: {unchanged:,}")
    print(f"  Not found: {not_found:,}")
    
    # Verify TX-15
    print("\nVerifying TX-15...")
    travis_tx15 = conn.execute('''
        SELECT COUNT(*) as count
        FROM voters
        WHERE county = 'Travis' AND congressional_district = '15'
    ''').fetchone()['count']
    
    if travis_tx15 == 0:
        print("✓ Travis County voters NOT in TX-15 (correct)")
    else:
        print(f"✗ Still have {travis_tx15} Travis County voters in TX-15")
    
    tx15_counties = conn.execute('''
        SELECT county, COUNT(*) as count
        FROM voters
        WHERE congressional_district = '15'
        GROUP BY county
        ORDER BY count DESC
        LIMIT 10
    ''').fetchall()
    
    print("\nTX-15 top counties:")
    for row in tx15_counties:
        print(f"  {row['county']}: {row['count']:,} voters")
    
    conn.close()
    
    print("\n" + "=" * 80)
    print("COMPLETE")
    print("=" * 80)
    print(f"\n✓ Congressional districts rebuilt")
    print(f"✓ Backup saved to: {backup_table}")
    print("\nNext: Regenerate cached reports")
    print("  python3 deploy/regenerate_district_cache_complete.py")

if __name__ == '__main__':
    main()
