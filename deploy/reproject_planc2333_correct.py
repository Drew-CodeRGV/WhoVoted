#!/usr/bin/env python3
"""Reproject PlanC2333 using exact .prj parameters."""
import json
import os
import sys
import tempfile
import urllib.request
import zipfile

try:
    import shapefile
    from pyproj import CRS, Transformer
except ImportError:
    print("Installing dependencies...")
    os.system(f"{sys.executable} -m pip install pyshp pyproj")
    import shapefile
    from pyproj import CRS, Transformer

# Download
url = 'https://data.capitol.texas.gov/dataset/748c952b-e926-4f44-8d01-a738884b3ec8/resource/5712ebe1-d777-4d4a-b836-0534e17bca01/download/planc2333.zip'

print("Downloading PlanC2333...")
tmpdir = tempfile.mkdtemp()
zip_path = os.path.join(tmpdir, 'plan.zip')
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
with urllib.request.urlopen(req, timeout=60) as resp:
    with open(zip_path, 'wb') as f:
        f.write(resp.read())

with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(tmpdir)

# Find shapefile
shp_path = None
for root, dirs, files in os.walk(tmpdir):
    for f in files:
        if f.lower().endswith('.shp'):
            shp_path = os.path.join(root, f)
            break

print(f"Reading {shp_path}")

# Read .prj file
prj_path = shp_path.replace('.shp', '.prj')
with open(prj_path) as f:
    prj_wkt = f.read()

print(f"Projection WKT: {prj_wkt[:200]}...")

# Create CRS from WKT
crs_from = CRS.from_wkt(prj_wkt)
crs_to = CRS.from_epsg(4326)  # WGS84

print(f"Source CRS: {crs_from.name}")
print(f"Target CRS: {crs_to.name}")

transformer = Transformer.from_crs(crs_from, crs_to, always_xy=True)

# Read shapefile
sf = shapefile.Reader(shp_path)

def reproject_coords(coords):
    """Recursively reproject coordinates."""
    if isinstance(coords[0], (int, float)):
        # Single coordinate pair
        lng, lat = transformer.transform(coords[0], coords[1])
        return [lng, lat]
    else:
        # List of coordinates
        return [reproject_coords(c) for c in coords]

# Find District 15
for sr in sf.shapeRecords():
    if sr.record[0] == 15:  # District field
        print(f"\nFound District 15")
        
        geom = sr.shape.__geo_interface__
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
                'district_name': 'TX-15 Congressional District (PlanC2333)',
                'color': '#3b82f6',
                'plan': 'PlanC2333',
                'year': '2026'
            }
        }
        
        # Calculate bounds
        if geom['type'] == 'Polygon':
            all_coords = geom['coordinates'][0]
        else:
            all_coords = [c for ring in geom['coordinates'][0] for c in ring]
        
        lngs = [c[0] for c in all_coords]
        lats = [c[1] for c in all_coords]
        
        print(f"\nReprojected bounds:")
        print(f"  Longitude: {min(lngs):.4f} to {max(lngs):.4f}")
        print(f"  Latitude: {min(lats):.4f} to {max(lats):.4f}")
        print(f"  Center: [{(min(lngs)+max(lngs))/2:.4f}, {(min(lats)+max(lats))/2:.4f}]")
        
        # Verify coordinates are in Texas
        if -107 < min(lngs) and max(lngs) < -93 and 25 < min(lats) and max(lats) < 37:
            print("✓ Coordinates are in Texas!")
            
            output = {'type': 'FeatureCollection', 'features': [feature]}
            
            output_path = sys.argv[1] if len(sys.argv) > 1 else '../public/d15/tx15_boundary.json'
            with open(output_path, 'w') as f:
                json.dump(output, f)
            
            print(f"\n✓ Saved PlanC2333 TX-15 to {output_path}")
        else:
            print("✗ Coordinates outside Texas range!")
            print(f"  Got: lng {min(lngs):.2f} to {max(lngs):.2f}, lat {min(lats):.2f} to {max(lats):.2f}")
        
        break

print(f"\nNote: Temp files in {tmpdir}")
