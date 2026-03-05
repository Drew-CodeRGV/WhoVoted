#!/usr/bin/env python3
"""Download PlanC2333 and reproject TX-15 to WGS84."""
import json
import os
import sys
import tempfile
import urllib.request
import zipfile

try:
    import shapefile
    from pyproj import Transformer
except ImportError:
    print("Installing dependencies...")
    os.system(f"{sys.executable} -m pip install pyshp pyproj")
    import shapefile
    from pyproj import Transformer

# Download and extract
url = 'https://data.capitol.texas.gov/dataset/748c952b-e926-4f44-8d01-a738884b3ec8/resource/5712ebe1-d777-4d4a-b836-0534e17bca01/download/planc2333.zip'

print("Downloading PlanC2333...")
with tempfile.TemporaryDirectory() as tmpdir:
    zip_path = os.path.join(tmpdir, 'plan.zip')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(zip_path, 'wb') as f:
            f.write(resp.read())
    
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(tmpdir)
    
    shp_path = None
    for root, dirs, files in os.walk(tmpdir):
        for f in files:
            if f.lower().endswith('.shp'):
                shp_path = os.path.join(root, f)
                break
    
    print(f"Reading {shp_path}...")
    sf = shapefile.Reader(shp_path)
    
    # NAD83 / Texas South Central (ftUS) to WGS84
    transformer = Transformer.from_crs("EPSG:2278", "EPSG:4326", always_xy=True)
    
    def reproject_coords(coords):
        if isinstance(coords[0], (int, float)):
            return list(transformer.transform(coords[0], coords[1]))
        return [reproject_coords(c) for c in coords]
    
    # Find and reproject TX-15
    for sr in sf.shapeRecords():
        dist = sr.record[0]  # District field
        if dist == 15:
            geom = sr.shape.__geo_interface__
            print(f"Found District {dist}")
            print(f"Original bbox: {sr.shape.bbox}")
            
            # Reproject
            geom['coordinates'] = reproject_coords(geom['coordinates'])
            
            # Create feature
            feature = {
                'type': 'Feature',
                'geometry': geom,
                'properties': {
                    'district_type': 'congressional',
                    'district_id': 'TX-15',
                    'district_name': 'TX-15 Congressional District',
                    'color': '#DC143C',
                    'plan': 'PlanC2333'
                }
            }
            
            # Calculate bounds
            if geom['type'] == 'Polygon':
                all_coords = geom['coordinates'][0]
            else:
                all_coords = [c for ring in geom['coordinates'][0] for c in ring]
            
            lngs = [c[0] for c in all_coords]
            lats = [c[1] for c in all_coords]
            
            print(f"Reprojected bounds:")
            print(f"  Lng: {min(lngs):.4f} to {max(lngs):.4f}")
            print(f"  Lat: {min(lats):.4f} to {max(lats):.4f}")
            print(f"  Center: [{(min(lngs)+max(lngs))/2:.4f}, {(min(lats)+max(lats))/2:.4f}]")
            
            # Save just TX-15
            output = {
                'type': 'FeatureCollection',
                'features': [feature]
            }
            
            output_path = sys.argv[1] if len(sys.argv) > 1 else '../public/d15/tx15_only.json'
            with open(output_path, 'w') as f:
                json.dump(output, f)
            
            print(f"\n✓ Saved TX-15 to {output_path}")
            break
