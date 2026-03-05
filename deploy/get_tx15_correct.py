#!/usr/bin/env python3
"""Get TX-15 boundary with correct projection using ogr2ogr."""
import json
import os
import sys
import tempfile
import urllib.request
import zipfile
import subprocess

# Download PlanC2333
url = 'https://data.capitol.texas.gov/dataset/748c952b-e926-4f44-8d01-a738884b3ec8/resource/5712ebe1-d777-4d4a-b836-0534e17bca01/download/planc2333.zip'

print("Downloading PlanC2333...")
with tempfile.TemporaryDirectory() as tmpdir:
    zip_path = os.path.join(tmpdir, 'plan.zip')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(zip_path, 'wb') as f:
            f.write(resp.read())
    
    print("Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(tmpdir)
    
    # Find shapefile
    shp_path = None
    for root, dirs, files in os.walk(tmpdir):
        for f in files:
            if f.lower().endswith('.shp'):
                shp_path = os.path.join(root, f)
                break
    
    print(f"Found: {shp_path}")
    
    # Use ogr2ogr to reproject and filter to District 15
    output_path = sys.argv[1] if len(sys.argv) > 1 else '../public/d15/tx15_boundary.json'
    
    try:
        # Try ogr2ogr (GDAL)
        cmd = [
            'ogr2ogr',
            '-f', 'GeoJSON',
            '-t_srs', 'EPSG:4326',  # WGS84
            '-where', 'District=15',
            output_path,
            shp_path
        ]
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"\n✓ Created {output_path}")
            
            # Read and show bounds
            with open(output_path) as f:
                data = json.load(f)
            
            if data['features']:
                feat = data['features'][0]
                coords = feat['geometry']['coordinates']
                if feat['geometry']['type'] == 'Polygon':
                    all_coords = coords[0]
                else:
                    all_coords = [c for ring in coords[0] for c in ring]
                
                lngs = [c[0] for c in all_coords]
                lats = [c[1] for c in all_coords]
                
                print(f"\nTX-15 bounds:")
                print(f"  Longitude: {min(lngs):.4f} to {max(lngs):.4f}")
                print(f"  Latitude: {min(lats):.4f} to {max(lats):.4f}")
                print(f"  Center: [{(min(lngs)+max(lngs))/2:.4f}, {(min(lats)+max(lats))/2:.4f}]")
                
                # Update properties
                feat['properties'] = {
                    'district_type': 'congressional',
                    'district_id': 'TX-15',
                    'district_name': 'TX-15 Congressional District',
                    'color': '#3b82f6',
                    'plan': 'PlanC2333'
                }
                
                with open(output_path, 'w') as f:
                    json.dump(data, f)
                
                print(f"✓ Updated properties")
        else:
            print(f"Error: {result.stderr}")
            print("\nogr2ogr not available, trying manual method...")
            raise Exception("ogr2ogr failed")
            
    except Exception as e:
        print(f"\nFalling back to manual reprojection...")
        # Manual method using pyproj
        try:
            import shapefile
            from pyproj import Transformer
        except ImportError:
            print("Installing dependencies...")
            os.system(f"{sys.executable} -m pip install pyshp pyproj")
            import shapefile
            from pyproj import Transformer
        
        sf = shapefile.Reader(shp_path)
        
        # Read .prj file to get exact projection
        prj_path = shp_path.replace('.shp', '.prj')
        if os.path.exists(prj_path):
            with open(prj_path) as f:
                prj_text = f.read()
                print(f"Projection: {prj_text[:200]}...")
        
        # Try EPSG:2278 (NAD83 / Texas South Central ftUS)
        transformer = Transformer.from_crs("EPSG:2278", "EPSG:4326", always_xy=True)
        
        for sr in sf.shapeRecords():
            if sr.record[0] == 15:  # District field
                geom = sr.shape.__geo_interface__
                
                def reproject(coords):
                    if isinstance(coords[0], (int, float)):
                        return list(transformer.transform(coords[0], coords[1]))
                    return [reproject(c) for c in coords]
                
                geom['coordinates'] = reproject(geom['coordinates'])
                
                feature = {
                    'type': 'Feature',
                    'geometry': geom,
                    'properties': {
                        'district_type': 'congressional',
                        'district_id': 'TX-15',
                        'district_name': 'TX-15 Congressional District',
                        'color': '#3b82f6',
                        'plan': 'PlanC2333'
                    }
                }
                
                output = {'type': 'FeatureCollection', 'features': [feature]}
                
                with open(output_path, 'w') as f:
                    json.dump(output, f)
                
                print(f"✓ Created {output_path} (manual method)")
                break

if __name__ == '__main__':
    main()
