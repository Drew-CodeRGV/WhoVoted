#!/usr/bin/env python3
"""Determine which counties a district covers by analyzing the boundary geometry.

This script:
1. Loads the district boundary (GeoJSON polygon)
2. Gets all unique counties from the voters table
3. For each county, checks if ANY voters in that county fall within the district boundary
4. Reports which counties the district actually covers
"""

import json
import sqlite3
from shapely.geometry import shape, Point
from collections import defaultdict

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'

def point_in_polygon(lng, lat, geometry):
    """Check if a point is inside a polygon using shapely."""
    point = Point(lng, lat)
    polygon = shape(geometry)
    return polygon.contains(point)

def determine_counties_in_district(district_id):
    """Determine which counties a district covers by checking voter locations."""
    
    # Load district boundary
    with open(DISTRICTS_FILE, 'r') as f:
        districts_data = json.load(f)
    
    district_feature = None
    for feature in districts_data['features']:
        if feature['properties']['district_id'] == district_id:
            district_feature = feature
            break
    
    if not district_feature:
        print(f"ERROR: District {district_id} not found in {DISTRICTS_FILE}")
        return
    
    district_geometry = district_feature['geometry']
    district_name = district_feature['properties']['district_name']
    
    print(f"\n{'='*80}")
    print(f"DETERMINING COUNTIES IN {district_name}")
    print(f"{'='*80}\n")
    
    # Connect to database
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get all unique counties that have geocoded voters
    counties = conn.execute("""
        SELECT DISTINCT county
        FROM voters
        WHERE geocoded = 1
        AND lat IS NOT NULL
        AND lng IS NOT NULL
        AND county IS NOT NULL
        AND county != ''
        ORDER BY county
    """).fetchall()
    
    print(f"Checking {len(counties)} counties for intersection with district boundary...\n")
    
    counties_in_district = []
    county_voter_counts = {}
    
    for county_row in counties:
        county = county_row['county']
        
        # Sample voters from this county to see if any fall in the district
        # We'll check up to 100 geocoded voters per county
        sample_voters = conn.execute("""
            SELECT vuid, lat, lng
            FROM voters
            WHERE county = ?
            AND geocoded = 1
            AND lat IS NOT NULL
            AND lng IS NOT NULL
            LIMIT 100
        """, (county,)).fetchall()
        
        voters_in_district = 0
        for voter in sample_voters:
            if point_in_polygon(voter['lng'], voter['lat'], district_geometry):
                voters_in_district += 1
        
        if voters_in_district > 0:
            # This county has voters in the district
            # Now count ALL voters in this county that fall in the district
            all_county_voters = conn.execute("""
                SELECT vuid, lat, lng
                FROM voters
                WHERE county = ?
                AND geocoded = 1
                AND lat IS NOT NULL
                AND lng IS NOT NULL
            """, (county,)).fetchall()
            
            total_in_district = 0
            for voter in all_county_voters:
                if point_in_polygon(voter['lng'], voter['lat'], district_geometry):
                    total_in_district += 1
            
            counties_in_district.append(county)
            county_voter_counts[county] = {
                'total_geocoded': len(all_county_voters),
                'in_district': total_in_district,
                'percentage': (total_in_district / len(all_county_voters) * 100) if len(all_county_voters) > 0 else 0
            }
            
            print(f"✓ {county:20s} - {total_in_district:>6,} / {len(all_county_voters):>6,} voters in district ({county_voter_counts[county]['percentage']:>5.1f}%)")
    
    conn.close()
    
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}\n")
    print(f"District: {district_name}")
    print(f"Counties in district: {len(counties_in_district)}")
    print(f"\nCounties:")
    for i, county in enumerate(sorted(counties_in_district), 1):
        stats = county_voter_counts[county]
        print(f"  {i}. {county} ({stats['in_district']:,} voters, {stats['percentage']:.1f}% of county)")
    print()
    
    return counties_in_district, county_voter_counts

if __name__ == '__main__':
    import sys
    
    # Check for shapely
    try:
        import shapely
    except ImportError:
        print("ERROR: shapely library not installed")
        print("Install with: pip install shapely")
        sys.exit(1)
    
    # Determine counties for each congressional district
    for district_id in ['TX-15', 'TX-28', 'TX-34']:
        determine_counties_in_district(district_id)
