#!/usr/bin/env python3
"""Reproject districts from State Plane to WGS84 (lat/long)."""
import json
import sys

try:
    from pyproj import Transformer
except ImportError:
    print("Installing pyproj...")
    import os
    os.system(f"{sys.executable} -m pip install pyproj")
    from pyproj import Transformer

def reproject_coordinates(coords, transformer):
    """Recursively reproject coordinates."""
    if isinstance(coords[0], (int, float)):
        # Single coordinate pair
        lng, lat = transformer.transform(coords[0], coords[1])
        return [lng, lat]
    else:
        # List of coordinates
        return [reproject_coordinates(c, transformer) for c in coords]

def reproject_geometry(geom, transformer):
    """Reproject a GeoJSON geometry."""
    new_geom = geom.copy()
    new_geom['coordinates'] = reproject_coordinates(geom['coordinates'], transformer)
    return new_geom

def main():
    input_file = sys.argv[1] if len(sys.argv) > 1 else '../public/d15/districts_d15.json'
    output_file = input_file
    
    print(f"Reading {input_file}...")
    with open(input_file) as f:
        data = json.load(f)
    
    # Check first coordinate to see scale
    test_feat = data['features'][0]
    test_coords = test_feat['geometry']['coordinates']
    if test_feat['geometry']['type'] == 'Polygon':
        sample_x, sample_y = test_coords[0][0]
    else:  # MultiPolygon
        sample_x, sample_y = test_coords[0][0][0]
    
    print(f"Sample coordinate: ({sample_x}, {sample_y})")
    
    # These are clearly in feet (values > 100,000)
    # Texas State Plane South Central in feet
    print("\nUsing NAD83 / Texas South Central (ftUS) - EPSG:2278")
    transformer = Transformer.from_crs("EPSG:2278", "EPSG:4326", always_xy=True)
    
    # Reproject all features
    reprojected_count = 0
    for feature in data['features']:
        feature['geometry'] = reproject_geometry(feature['geometry'], transformer)
        reprojected_count += 1
        if reprojected_count <= 3:
            # Show first few
            if feature['geometry']['type'] == 'Polygon':
                sample = feature['geometry']['coordinates'][0][0]
            else:
                sample = feature['geometry']['coordinates'][0][0][0]
            print(f"  {feature['properties']['district_id']}: {sample}")
    
    # Save
    with open(output_file, 'w') as f:
        json.dump(data, f)
    
    print(f"\n✓ Reprojected {len(data['features'])} features")
    print(f"✓ Saved to {output_file}")
    
    # Show TX-15 bounds
    tx15 = next((f for f in data['features'] if f['properties']['district_id'] == 'TX-15'), None)
    if tx15:
        coords = tx15['geometry']['coordinates']
        if tx15['geometry']['type'] == 'Polygon':
            all_coords = coords[0]
        else:
            all_coords = [c for ring in coords[0] for c in ring]
        
        lngs = [c[0] for c in all_coords]
        lats = [c[1] for c in all_coords]
        print(f"\nTX-15 bounds:")
        print(f"  Longitude: {min(lngs):.4f} to {max(lngs):.4f}")
        print(f"  Latitude: {min(lats):.4f} to {max(lats):.4f}")
        print(f"  Center: [{(min(lngs)+max(lngs))/2:.4f}, {(min(lats)+max(lats))/2:.4f}]")

if __name__ == '__main__':
    main()
