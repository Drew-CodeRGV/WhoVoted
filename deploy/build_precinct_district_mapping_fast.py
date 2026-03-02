#!/usr/bin/env python3
"""
Fast precinct-to-district mapping using centroid-only method.

This simplified version only uses precinct centroids (center points) to determine
if a precinct belongs to a district. This is much faster than overlap calculations
and is accurate enough for most use cases.
"""

import json
import sqlite3
from pathlib import Path
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

def get_polygon_centroid(coords):
    """Calculate centroid of a polygon using simple average."""
    if not coords or not coords[0]:
        return None
    
    # Get first ring (exterior)
    ring = coords[0]
    if len(ring) < 3:
        return None
    
    # Calculate average lat/lng
    total_lng = sum(p[0] for p in ring)
    total_lat = sum(p[1] for p in ring)
    count = len(ring)
    
    return (total_lng / count, total_lat / count)

def point_in_polygon_simple(lng, lat, geometry):
    """Simple ray-casting algorithm for point-in-polygon test."""
    gtype = geometry.get('type', '')
    coords = geometry.get('coordinates', [])
    
    if gtype == 'Polygon':
        return _point_in_ring(lng, lat, coords[0])
    elif gtype == 'MultiPolygon':
        for poly in coords:
            if _point_in_ring(lng, lat, poly[0]):
                return True
        return False
    return False

def _point_in_ring(lng, lat, ring):
    """Ray-casting algorithm for a single ring."""
    inside = False
    n = len(ring)
    p1_lng, p1_lat = ring[0]
    
    for i in range(1, n + 1):
        p2_lng, p2_lat = ring[i % n]
        if lat > min(p1_lat, p2_lat):
            if lat <= max(p1_lat, p2_lat):
                if lng <= max(p1_lng, p2_lng):
                    if p1_lat != p2_lat:
                        x_inters = (lat - p1_lat) * (p2_lng - p1_lng) / (p2_lat - p1_lat) + p1_lng
                    if p1_lng == p2_lng or lng <= x_inters:
                        inside = not inside
        p1_lng, p1_lat = p2_lng, p2_lat
    
    return inside

def normalize_precinct_id(precinct_id):
    """Normalize precinct ID for matching.
    
    Handles various formats:
    - "0001" -> "1", "001", "01", "0001"
    - "S 101." -> "101"
    - "1041" -> "1041"
    """
    if not precinct_id:
        return []
    
    # Remove common prefixes and suffixes
    pid = str(precinct_id).strip()
    pid = pid.replace('S ', '').replace('.', '').strip()
    
    # Generate variations
    variations = [pid]
    
    # If it's numeric, add versions with/without leading zeros
    if pid.isdigit():
        # Remove leading zeros
        no_zeros = pid.lstrip('0') or '0'
        variations.append(no_zeros)
        
        # Add versions with different zero padding
        variations.append(pid.zfill(2))  # 2 digits
        variations.append(pid.zfill(3))  # 3 digits
        variations.append(pid.zfill(4))  # 4 digits
    
    return list(set(variations))  # Remove duplicates

def main():
    print("=" * 60)
    print("Building Precinct-to-District Mapping (Fast Version)")
    print("=" * 60)
    
    start_time = time.time()
    
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
    precinct_centroids = {}
    
    for pfile in PRECINCT_FILES:
        pdata = load_geojson(pfile)
        if pdata:
            precincts = pdata.get('features', [])
            for precinct in precincts:
                props = precinct.get('properties', {})
                precinct_id = props.get('precinct_id') or props.get('precinct', '')
                
                if not precinct_id:
                    continue
                
                geom = precinct.get('geometry')
                if not geom:
                    continue
                
                # Calculate centroid
                coords = geom.get('coordinates', [])
                gtype = geom.get('type', '')
                
                centroid = None
                if gtype == 'Polygon':
                    centroid = get_polygon_centroid(coords)
                elif gtype == 'MultiPolygon' and coords:
                    centroid = get_polygon_centroid(coords[0])
                
                if centroid:
                    # Store all variations of the precinct ID
                    variations = normalize_precinct_id(precinct_id)
                    for var in variations:
                        precinct_centroids[var] = {
                            'lng': centroid[0],
                            'lat': centroid[1],
                            'geometry': geom,
                            'original_id': str(precinct_id)
                        }
            
            all_precincts.extend(precincts)
            print(f"   Loaded {len(precincts)} precincts from {pfile.name}")
    
    print(f"   Total precincts: {len(all_precincts)}")
    print(f"   Precincts with centroids: {len(precinct_centroids)}")
    
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
        
        print(f"   [{i+1}/{len(districts)}] {district_name}...", end='', flush=True)
        
        district_geom = district.get('geometry')
        if not district_geom:
            print(" No geometry, skipping")
            continue
        
        # Find precincts whose centroid is inside this district
        matching_precincts = []
        matching_original_ids = set()
        
        for precinct_id, precinct_data in precinct_centroids.items():
            lng = precinct_data['lng']
            lat = precinct_data['lat']
            original_id = precinct_data.get('original_id', precinct_id)
            
            if point_in_polygon_simple(lng, lat, district_geom):
                # Only add each original precinct once (avoid duplicates from variations)
                if original_id not in matching_original_ids:
                    matching_precincts.append(precinct_id)
                    matching_original_ids.add(original_id)
        
        print(f" {len(matching_precincts)} precincts")
        
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
        db_precincts.add(str(row[0]))
    
    # Get all unique precincts from voter_elections table
    for row in conn.execute("SELECT DISTINCT precinct FROM voter_elections WHERE precinct IS NOT NULL AND precinct != ''"):
        db_precincts.add(str(row[0]))
    
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
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("✅ Precinct-to-District Mapping Complete!")
    print("=" * 60)
    print(f"\nCompleted in {elapsed:.1f} seconds")
    print(f"Mapping file: {OUTPUT_FILE}")
    print(f"Districts mapped: {len(mapping)}")
    print(f"Precincts mapped: {len(mapped_precincts)}")
    print("\nNext steps:")
    print("1. Update backend to use precinct-based queries for districts")
    print("2. Regenerate district cache files using precinct lookups")
    print("3. Enjoy instant district reports! 🚀")

if __name__ == '__main__':
    main()
