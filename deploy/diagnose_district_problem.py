#!/usr/bin/env python3
"""Diagnose why Travis County voters are being assigned to TX-15."""

import sqlite3
import json

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=" * 70)
print("DIAGNOSING DISTRICT ASSIGNMENT PROBLEM")
print("=" * 70)

# Sample some Travis County voters assigned to TX-15
print("\nSAMPLE: Travis County voters assigned to TX-15:")
print("-" * 70)
travis_tx15 = conn.execute("""
    SELECT vuid, firstname, lastname, address, lat, lng, congressional_district
    FROM voters
    WHERE county = 'Travis'
    AND congressional_district = '15'
    LIMIT 10
""").fetchall()

for row in travis_tx15:
    print(f"  {row[1]} {row[2]}")
    print(f"    Address: {row[3]}")
    print(f"    Coords: {row[4]}, {row[5]}")
    print(f"    District: {row[6]}")
    print()

# Check the boundary file
print("\nCHECKING BOUNDARY FILE:")
print("-" * 70)

try:
    with open('/opt/whovoted/public/data/districts.json') as f:
        districts_data = json.load(f)
    
    print(f"Boundary file contains {len(districts_data['features'])} features")
    
    # Find TX-15
    tx15_feature = None
    for feature in districts_data['features']:
        if feature['properties'].get('district_id') == 'TX-15':
            tx15_feature = feature
            break
    
    if tx15_feature:
        print(f"\nTX-15 found in boundary file:")
        print(f"  District Name: {tx15_feature['properties'].get('district_name')}")
        print(f"  District Type: {tx15_feature['properties'].get('district_type')}")
        print(f"  Geometry Type: {tx15_feature['geometry']['type']}")
        
        # Get bounding box
        coords = tx15_feature['geometry']['coordinates']
        if tx15_feature['geometry']['type'] == 'Polygon':
            all_coords = coords[0]
        elif tx15_feature['geometry']['type'] == 'MultiPolygon':
            all_coords = []
            for poly in coords:
                all_coords.extend(poly[0])
        
        lngs = [c[0] for c in all_coords]
        lats = [c[1] for c in all_coords]
        
        print(f"\n  Bounding Box:")
        print(f"    Longitude: {min(lngs):.4f} to {max(lngs):.4f}")
        print(f"    Latitude: {min(lats):.4f} to {max(lats):.4f}")
        
        # Travis County is around 30.27°N, -97.74°W
        # Hidalgo County is around 26.25°N, -98.15°W
        print(f"\n  Reference:")
        print(f"    Travis County (Austin): ~30.27°N, -97.74°W")
        print(f"    Hidalgo County (McAllen): ~26.25°N, -98.15°W")
        
        if max(lats) > 29:
            print(f"\n  ⚠ WARNING: TX-15 boundary extends north of 29°N")
            print(f"    This would include Central Texas (Travis County area)")
            print(f"    TX-15 should only cover South Texas!")
    else:
        print(f"\n✗ TX-15 not found in boundary file!")
        
except Exception as e:
    print(f"Error reading boundary file: {e}")

# Check if there's a backup
print("\nCHECKING FOR BACKUP:")
print("-" * 70)
backup_exists = conn.execute("""
    SELECT name FROM sqlite_master 
    WHERE type='table' AND name LIKE 'voters_districts_backup%'
    ORDER BY name DESC
    LIMIT 1
""").fetchone()

if backup_exists:
    backup_table = backup_exists[0]
    print(f"Found backup table: {backup_table}")
    
    # Check what Travis County voters had before
    travis_before = conn.execute(f"""
        SELECT congressional_district, COUNT(*) as count
        FROM {backup_table}
        WHERE county = 'Travis'
        GROUP BY congressional_district
        ORDER BY count DESC
        LIMIT 5
    """).fetchall()
    
    print(f"\nTravis County districts BEFORE fix:")
    for district, count in travis_before:
        print(f"  {district or 'NO ASSIGNMENT':20s}: {count:,} voters")
else:
    print(f"No backup table found")

conn.close()

print("\n" + "=" * 70)
print("CONCLUSION:")
print("=" * 70)
print("The TX-15 boundary file is likely incorrect or too broad.")
print("It's assigning voters from Travis County (Central Texas) to TX-15 (South Texas).")
print("\nThe user said: 'the geo file for the geo boundary .. the actual shape")
print("and boundary file, needs to stay .. it took a long time to get the correct one setup'")
print("\nBut the boundary file appears to be WRONG!")
print("=" * 70)
