#!/usr/bin/env python3
"""
Add old_congressional_district column and populate it based on PlanC2193 (2022-2024) boundaries.
This allows fast redistricting comparisons without slow point-in-polygon calculations.
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')

import database as db
import json
from pathlib import Path
from shapely.geometry import shape, Point
from shapely.prepared import prep

def point_in_polygon_shapely(lng, lat, geometry):
    """Fast point-in-polygon using Shapely"""
    point = Point(lng, lat)
    polygon = shape(geometry)
    return polygon.contains(point)

def main():
    print("Adding old_congressional_district column...")
    
    conn = db.get_connection()
    
    # Add column if it doesn't exist
    try:
        conn.execute("ALTER TABLE voters ADD COLUMN old_congressional_district TEXT")
        print("✓ Added old_congressional_district column")
    except Exception as e:
        if "duplicate column" in str(e).lower():
            print("✓ Column already exists")
        else:
            raise
    
    # Load old congressional boundaries (PlanC2193)
    old_boundaries_file = Path('/opt/whovoted/public/data/districts_old_congressional.json')
    if not old_boundaries_file.exists():
        print(f"ERROR: Old boundaries file not found: {old_boundaries_file}")
        print("Please ensure the PlanC2193 GeoJSON file is available")
        return
    
    with open(old_boundaries_file, 'r') as f:
        old_boundaries = json.load(f)
    
    print(f"Loaded {len(old_boundaries['features'])} old congressional districts")
    
    # Prepare geometries for fast lookup
    district_geometries = {}
    for feature in old_boundaries['features']:
        district_id = feature['properties'].get('district_id') or feature['properties'].get('DISTRICT')
        if district_id:
            # Use prepared geometry for faster contains checks
            geom = shape(feature['geometry'])
            district_geometries[district_id] = prep(geom)
    
    print(f"Prepared {len(district_geometries)} district geometries")
    
    # Get all voters with coordinates
    voters = conn.execute("""
        SELECT vuid, lat, lng, congressional_district
        FROM voters
        WHERE lat IS NOT NULL AND lng IS NOT NULL
        ORDER BY vuid
    """).fetchall()
    
    print(f"Processing {len(voters)} voters with coordinates...")
    
    # Process in batches
    batch_size = 1000
    updated = 0
    not_found = 0
    
    for i in range(0, len(voters), batch_size):
        batch = voters[i:i+batch_size]
        updates = []
        
        for voter in batch:
            vuid = voter['vuid']
            lat = voter['lat']
            lng = voter['lng']
            point = Point(lng, lat)
            
            # Find which old district this voter was in
            old_district = None
            for district_id, prepared_geom in district_geometries.items():
                if prepared_geom.contains(point):
                    old_district = district_id
                    break
            
            if old_district:
                updates.append((old_district, vuid))
            else:
                not_found += 1
        
        # Batch update
        if updates:
            conn.executemany("""
                UPDATE voters 
                SET old_congressional_district = ?
                WHERE vuid = ?
            """, updates)
            updated += len(updates)
        
        if (i + batch_size) % 10000 == 0:
            print(f"  Processed {i + batch_size:,} voters... (updated: {updated:,}, not found: {not_found:,})")
    
    conn.commit()
    
    print(f"\n✓ Complete!")
    print(f"  Updated: {updated:,} voters")
    print(f"  Not found in old boundaries: {not_found:,} voters")
    
    # Show summary by district
    print("\nOld district assignments:")
    summary = conn.execute("""
        SELECT old_congressional_district, COUNT(*) as count
        FROM voters
        WHERE old_congressional_district IS NOT NULL
        GROUP BY old_congressional_district
        ORDER BY old_congressional_district
    """).fetchall()
    
    for row in summary:
        print(f"  {row['old_congressional_district']}: {row['count']:,} voters")

if __name__ == '__main__':
    main()
