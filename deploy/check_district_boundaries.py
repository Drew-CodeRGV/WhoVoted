#!/usr/bin/env python3
"""Check if the district boundaries are correct."""

import sqlite3
import json

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=" * 70)
print("DISTRICT BOUNDARY CHECK")
print("=" * 70)

# Check how many voters are in each district
print("\nVoters by Congressional District (all registered):")
print("-" * 70)
districts = conn.execute("""
    SELECT 
        congressional_district,
        COUNT(*) as total,
        COUNT(DISTINCT county) as counties
    FROM voters
    WHERE geocoded = 1
    AND congressional_district IS NOT NULL
    AND congressional_district != ''
    GROUP BY congressional_district
    ORDER BY total DESC
""").fetchall()

for district, total, counties in districts:
    print(f"  TX-{district:2s}: {total:7,} voters across {counties:2d} counties")

# Check how many voted in 2026
print("\nVoters by Congressional District (voted in 2026):")
print("-" * 70)
voted_2026 = conn.execute("""
    SELECT 
        v.congressional_district,
        COUNT(*) as total,
        COUNT(DISTINCT v.county) as counties
    FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.geocoded = 1
    AND v.congressional_district IS NOT NULL
    AND v.congressional_district != ''
    AND ve.election_date = '2026-03-03'
    GROUP BY v.congressional_district
    ORDER BY total DESC
""").fetchall()

for district, total, counties in voted_2026:
    print(f"  TX-{district:2s}: {total:7,} voters across {counties:2d} counties")

# Check the boundary file
print("\nBoundary file check:")
print("-" * 70)
with open('/opt/whovoted/public/data/districts.json') as f:
    districts_data = json.load(f)

congressional_districts = [f for f in districts_data['features'] if f['properties'].get('district_type') == 'congressional']
print(f"Congressional districts in boundary file: {len(congressional_districts)}")
for feature in congressional_districts:
    props = feature['properties']
    print(f"  {props.get('district_id')}: {props.get('district_name')}")

# Check if TX-28 and TX-34 boundaries are too small
print("\nBoundary sizes:")
print("-" * 70)
for feature in congressional_districts:
    props = feature['properties']
    district_id = props.get('district_id')
    
    # Get bounding box
    coords = feature['geometry']['coordinates']
    if feature['geometry']['type'] == 'Polygon':
        all_coords = coords[0]
    elif feature['geometry']['type'] == 'MultiPolygon':
        all_coords = []
        for poly in coords:
            all_coords.extend(poly[0])
    
    lngs = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]
    
    print(f"\n  {district_id}:")
    print(f"    Longitude: {min(lngs):.4f} to {max(lngs):.4f} (width: {max(lngs)-min(lngs):.4f}°)")
    print(f"    Latitude: {min(lats):.4f} to {max(lats):.4f} (height: {max(lats)-min(lats):.4f}°)")

conn.close()

print("\n" + "=" * 70)
print("CONCLUSION:")
print("=" * 70)
print("If TX-28 and TX-34 have very few voters, the boundary polygons")
print("might be too small or incorrectly defined.")
print("=" * 70)
