#!/usr/bin/env python3
"""Fix district assignments CORRECTLY - only assign to geocoded voters."""

import sqlite3
import json
from shapely.geometry import shape, Point

print("=" * 70)
print("FIXING DISTRICT ASSIGNMENTS CORRECTLY")
print("=" * 70)

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# Step 1: Clear ALL district assignments
print("\nStep 1: Clearing all district assignments...")
print("-" * 70)

conn.execute("UPDATE voters SET congressional_district = NULL")
conn.execute("UPDATE voters SET state_house_district = NULL")
conn.execute("UPDATE voters SET commissioner_district = NULL")
conn.commit()

print("✓ All district assignments cleared")

# Step 2: Load boundary file
print("\nStep 2: Loading boundary file...")
print("-" * 70)

with open('/opt/whovoted/public/data/districts.json') as f:
    districts_data = json.load(f)

print(f"✓ Loaded {len(districts_data['features'])} district boundaries")

# Step 3: Assign districts ONLY to geocoded voters
print("\nStep 3: Assigning districts to GEOCODED voters only...")
print("-" * 70)

# Get all geocoded voters
geocoded_voters = conn.execute("""
    SELECT vuid, lat, lng
    FROM voters
    WHERE geocoded = 1
    AND lat IS NOT NULL
    AND lng IS NOT NULL
""").fetchall()

print(f"Found {len(geocoded_voters):,} geocoded voters")

# Process each district
for feature in districts_data['features']:
    props = feature['properties']
    district_id = props.get('district_id', '')
    district_name = props.get('district_name', '')
    district_type = props.get('district_type', '')
    
    if not district_id or not district_type:
        continue
    
    print(f"\nProcessing {district_name}...")
    
    # Create shapely polygon
    polygon = shape(feature['geometry'])
    
    # Find voters in this district
    vuids_in_district = []
    for vuid, lat, lng in geocoded_voters:
        point = Point(lng, lat)
        if polygon.contains(point):
            vuids_in_district.append(vuid)
    
    if not vuids_in_district:
        print(f"  ⚠ No voters found in {district_name}")
        continue
    
    # Update database
    if district_type == 'congressional':
        # Extract just the number (15, 28, 34)
        district_num = district_id.replace('TX-', '')
        conn.executemany(
            "UPDATE voters SET congressional_district = ? WHERE vuid = ?",
            [(district_num, vuid) for vuid in vuids_in_district]
        )
    elif district_type == 'state_house':
        district_num = district_id.replace('HD-', '')
        conn.executemany(
            "UPDATE voters SET state_house_district = ? WHERE vuid = ?",
            [(district_num, vuid) for vuid in vuids_in_district]
        )
    elif district_type == 'commissioner':
        conn.executemany(
            "UPDATE voters SET commissioner_district = ? WHERE vuid = ?",
            [(district_id, vuid) for vuid in vuids_in_district]
        )
    
    conn.commit()
    print(f"  ✓ Assigned {len(vuids_in_district):,} voters to {district_name}")

# Step 4: Verify results
print("\n" + "=" * 70)
print("VERIFICATION")
print("=" * 70)

# Check that NO non-geocoded voters have districts
non_geocoded_with_district = conn.execute("""
    SELECT COUNT(*)
    FROM voters
    WHERE geocoded = 0
    AND (
        (congressional_district IS NOT NULL AND congressional_district != '')
        OR (state_house_district IS NOT NULL AND state_house_district != '')
        OR (commissioner_district IS NOT NULL AND commissioner_district != '')
    )
""").fetchone()[0]

if non_geocoded_with_district == 0:
    print(f"\n✓ PASS: No non-geocoded voters have district assignments")
else:
    print(f"\n✗ FAIL: {non_geocoded_with_district:,} non-geocoded voters still have districts!")

# Check Travis County
travis_stats = conn.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN geocoded = 1 THEN 1 ELSE 0 END) as geocoded,
        SUM(CASE WHEN congressional_district IS NOT NULL AND congressional_district != '' THEN 1 ELSE 0 END) as has_district
    FROM voters
    WHERE county = 'Travis'
""").fetchone()

print(f"\nTravis County:")
print(f"  Total: {travis_stats[0]:,}")
print(f"  Geocoded: {travis_stats[1]:,}")
print(f"  Has district: {travis_stats[2]:,}")

if travis_stats[2] == travis_stats[1]:
    print(f"  ✓ Only geocoded Travis voters have districts")
elif travis_stats[2] < travis_stats[1]:
    print(f"  ⚠ Some geocoded Travis voters don't have districts (outside boundary)")
else:
    print(f"  ✗ More voters have districts than are geocoded!")

# Check Hidalgo County
hidalgo_stats = conn.execute("""
    SELECT 
        congressional_district,
        COUNT(*) as count
    FROM voters
    WHERE county = 'Hidalgo'
    AND geocoded = 1
    GROUP BY congressional_district
    ORDER BY count DESC
""").fetchall()

print(f"\nHidalgo County (geocoded voters only):")
for district, count in hidalgo_stats:
    district_label = f"TX-{district}" if district else "NO ASSIGNMENT"
    print(f"  {district_label:20s}: {count:,}")

# Overall stats
overall = conn.execute("""
    SELECT 
        COUNT(*) as total_geocoded,
        SUM(CASE WHEN congressional_district IS NOT NULL AND congressional_district != '' THEN 1 ELSE 0 END) as has_cong,
        SUM(CASE WHEN state_house_district IS NOT NULL AND state_house_district != '' THEN 1 ELSE 0 END) as has_house
    FROM voters
    WHERE geocoded = 1
""").fetchone()

print(f"\nOverall (geocoded voters only):")
print(f"  Total geocoded: {overall[0]:,}")
print(f"  With Congressional: {overall[1]:,} ({overall[1]/overall[0]*100:.1f}%)")
print(f"  With State House: {overall[2]:,} ({overall[2]/overall[0]*100:.1f}%)")

conn.close()

print("\n" + "=" * 70)
print("DISTRICT ASSIGNMENTS FIXED")
print("=" * 70)
print("\nNext step: Regenerate cache files")
