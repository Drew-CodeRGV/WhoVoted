#!/usr/bin/env python3
"""
Build precinct-to-district mapping for fast district queries.

This script:
1. Loads all district boundaries (congressional, state house, commissioner)
2. Loads precinct boundary data
3. Determines which precincts fall within each district (using centroid or overlap)
4. Saves the mapping to a JSON file for fast lookups

This is a ONE-TIME computation that dramatically speeds up district queries.
Instead of checking millions of voter coordinates against district polygons,
we can simply query: "SELECT * FROM voters WHERE precinct IN (...)"
"""

import json
import sqlite3
from pathlib import Path
from shapely.geometry import shape, Point, Polygon, MultiPolygon
from shapely.ops import unary_union
import time

# Paths
DISTRICTS_FILE = Path('/opt/whovoted/public/data/districts.json')
PRECINCT_FILES = [
    Path('/opt/whovoted/public/data/precinct_boundaries.json'),
    Path('/opt/whovoted/public/data/precinct_boundaries_cameron.json'),
    Path('/opt/whovoted/public/data/precinct_boundaries_combined.json'),
]
OUTPUT_FILE = Path('/opt/whovoted/public/cache/precinct_district_mapping.json')
DB_PATH = Path('/opt/whovoted/data/whovoted.db')

def load_geojson(path):
    """Load GeoJSON file."""
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)

def get_precinct_centroid(precinct_geom):
    """Get the centroid of a precinct polygon."""
    try:
        geom = shape(precinct_geom)
        return geom.centroid
    except Exception as e:
        print(f"  Warning: Could not get centroid: {e}")
        return None

def precinct_overlaps_district(precinct_geom, district_geom, threshold=0.5):
    """Check if precinct overlaps with district by at least threshold (0-1)."""
    try:
        p_shape = shape(precinct_geom)
        d_shape = shape(district_geom)
        
        if not p_shape.is_valid:
            p_shape = p_shape.buffer(0)
        if not d_shape.is_valid:
            d_shape = d_shape.buffer(0)
        
        intersection = p_shape.intersection(d_shape)
        overlap_ratio = intersection.area / p_shape.area if p_shape.area > 0 else 0
        
        return overlap_ratio >= threshold
    except Exception as e:
        print(f"  Warning: Could not check overlap: {e}")
        return False

def main():
    print("=" * 60)
    print("Building Precinct-to-District Mapping")
    print("=" * 60)
    
    # Load districts
    print("\n1. Loading district boundaries...")
    districts_data = load_geojson(DISTRICTS_FILE)
    if not districts_data:
        print("ERROR: Could not load districts.json")
        return
    
    districts = districts_data.get('features', [])
    print(f"   Loaded {len(districts)} districts")
    
    # Load precincts
    print("\n2. Loading precinct boundaries...")
    all_precincts = []
    for pfile in PRECINCT_FILES:
        pdata = load_geojson(pfile)
        if pdata:
            precincts = pdata.get('features', [])
            all_precincts.extend(precincts)
            print(f"   Loaded {len(precincts)} precincts from {pfile.name}")
    
    print(f"   Total precincts: {len(all_precincts)}")
    
    # Build mapping: district_name -> [precinct_ids]
    print("\n3. Computing precinct-to-district mappings...")
    mapping = {}
    
    for i, district in enumerate(districts):
        props = district.get('properties', {})
        district_name = props.get('district_name', '')
        district_id = props.get('district_id', '')
        district_type = props.get('district_type', '')
        
        if not district_name:
            continue
        
        print(f"\n   [{i+1}/{len(districts)}] {district_name}")
        
        district_geom = district.get('geometry')
        if not district_geom:
            print("      No geometry, skipping")
            continue
        
        # Find precincts that overlap with this district
        matching_precincts = []
        
        for precinct in all_precincts:
            precinct_props = precinct.get('properties', {})
            precinct_id = precinct_props.get('precinct_id') or precinct_props.get('precinct', '')
            
            if not precinct_id:
                continue
            
            precinct_geom = precinct.get('geometry')
            if not precinct_geom:
                continue
            
            # Method 1: Check if precinct centroid is inside district (fast)
            centroid = get_precinct_centroid(precinct_geom)
            if centroid:
                try:
                    d_shape = shape(district_geom)
                    if d_shape.contains(centroid):
                        matching_precincts.append(str(precinct_id))
                        continue
                except:
                    pass
            
            # Method 2: Check if precinct overlaps district by at least 50% (slower but more accurate)
            if precinct_overlaps_district(precinct_geom, district_geom, threshold=0.5):
                if str(precinct_id) not in matching_precincts:
                    matching_precincts.append(str(precinct_id))
        
        print(f"      Found {len(matching_precincts)} precincts")
        
        mapping[district_name] = {
            'district_id': district_id,
            'district_type': district_type,
            'precincts': matching_precincts,
            'precinct_count': len(matching_precincts)
        }
    
    # Save mapping
    print(f"\n4. Saving mapping to {OUTPUT_FILE}...")
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"   ✓ Saved {len(mapping)} district mappings")
    
    # Verify with database
    print("\n5. Verifying precinct coverage in database...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get all unique precincts from voters table
    db_precincts = set()
    for row in conn.execute("SELECT DISTINCT precinct FROM voters WHERE precinct IS NOT NULL AND precinct != ''"):
        db_precincts.add(row[0])
    
    # Get all unique precincts from voter_elections table
    for row in conn.execute("SELECT DISTINCT precinct FROM voter_elections WHERE precinct IS NOT NULL AND precinct != ''"):
        db_precincts.add(row[0])
    
    print(f"   Database has {len(db_precincts)} unique precincts")
    
    # Check coverage
    mapped_precincts = set()
    for district_data in mapping.values():
        mapped_precincts.update(district_data['precincts'])
    
    print(f"   Mapped {len(mapped_precincts)} unique precincts to districts")
    
    unmapped = db_precincts - mapped_precincts
    if unmapped:
        print(f"   ⚠ {len(unmapped)} precincts in DB not mapped to any district:")
        for p in sorted(unmapped)[:20]:  # Show first 20
            count = conn.execute("SELECT COUNT(*) FROM voters WHERE precinct = ?", (p,)).fetchone()[0]
            print(f"      - {p} ({count} voters)")
        if len(unmapped) > 20:
            print(f"      ... and {len(unmapped) - 20} more")
    else:
        print("   ✓ All database precincts are mapped!")
    
    conn.close()
    
    print("\n" + "=" * 60)
    print("✅ Precinct-to-District Mapping Complete!")
    print("=" * 60)
    print(f"\nMapping file: {OUTPUT_FILE}")
    print(f"Districts mapped: {len(mapping)}")
    print(f"Precincts mapped: {len(mapped_precincts)}")
    print("\nNext steps:")
    print("1. Update backend to use precinct-based queries for districts")
    print("2. Regenerate district cache files using precinct lookups")
    print("3. Enjoy instant district reports! 🚀")

if __name__ == '__main__':
    main()
