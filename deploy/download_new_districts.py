#!/usr/bin/env python3
"""Download and inspect the new PlanC2333 congressional districts."""
import json
import os
import sys
import tempfile
import urllib.request
import zipfile

try:
    import shapefile
except ImportError:
    print("Installing pyshp...")
    os.system(f"{sys.executable} -m pip install pyshp")
    import shapefile

CD_COLORS = {
    '15': '#DC143C',
    '28': '#FF6347',
    '34': '#FF8C00',
    '27': '#B22222',
    '21': '#CD5C5C',
}

def download_and_extract(url, extract_dir):
    """Download a zip file and extract it."""
    print(f"Downloading {url}...")
    zip_path = os.path.join(extract_dir, 'download.zip')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible)'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(zip_path, 'wb') as f:
            f.write(resp.read())
    print(f"Extracting...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_dir)
    os.remove(zip_path)
    # Find .shp file
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.lower().endswith('.shp'):
                return os.path.join(root, f)
    return None

def main():
    output_dir = sys.argv[1] if len(sys.argv) > 1 else '../public/data'
    
    # Download PlanC2333
    plan_url = 'https://data.capitol.texas.gov/dataset/748c952b-e926-4f44-8d01-a738884b3ec8/resource/5712ebe1-d777-4d4a-b836-0534e17bca01/download/planc2333.zip'
    
    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = download_and_extract(plan_url, tmpdir)
        if not shp_path:
            print("ERROR: Could not find .shp file")
            sys.exit(1)
        
        print(f"\nReading shapefile: {shp_path}")
        sf = shapefile.Reader(shp_path)
        
        print(f"Fields: {[f[0] for f in sf.fields[1:]]}")
        print(f"Total districts: {len(sf)}")
        print(f"Bounding box: {sf.bbox}")
        
        # Convert all districts to GeoJSON
        features = []
        for sr in sf.shapeRecords():
            geom = sr.shape.__geo_interface__
            props = {}
            for i, field in enumerate(sf.fields[1:]):
                props[field[0]] = sr.record[i]
            
            # Extract district number
            dist_num = None
            for key in ['DISTRICT', 'District', 'CD', 'CONG_DIST', 'NAME', 'BASENAME', 'DISTRICT_N']:
                val = props.get(key)
                if val is not None:
                    val_str = str(val).strip().lstrip('0')
                    if val_str.isdigit():
                        dist_num = val_str
                        break
            
            if not dist_num:
                print(f"WARNING: Could not find district number in {props}")
                continue
            
            # Check if this district is relevant (15, 28, 34, etc.)
            if dist_num in ['15', '28', '34', '27', '21']:
                print(f"\nFound TX-{dist_num}:")
                print(f"  Properties: {props}")
                print(f"  Geometry type: {geom['type']}")
                
                color = CD_COLORS.get(dist_num, '#DC143C')
                feature = {
                    'type': 'Feature',
                    'geometry': geom,
                    'properties': {
                        'district_type': 'congressional',
                        'district_id': f'TX-{dist_num}',
                        'district_name': f'TX-{dist_num} Congressional District',
                        'color': color,
                        'plan': 'PlanC2333',
                        'redistricted': True
                    }
                }
                features.append(feature)
        
        print(f"\n\nFound {len(features)} relevant congressional districts")
        
        # Load existing districts.json
        districts_path = os.path.join(output_dir, 'districts.json')
        with open(districts_path) as f:
            districts = json.load(f)
        
        # Save old congressional districts
        old_cd = [f for f in districts['features'] if f['properties']['district_type'] == 'congressional']
        old_path = os.path.join(output_dir, 'districts_old_congressional.json')
        with open(old_path, 'w') as f:
            json.dump({'type': 'FeatureCollection', 'features': old_cd}, f)
        print(f"Saved {len(old_cd)} old districts to {old_path}")
        
        # Replace congressional districts
        non_cd = [f for f in districts['features'] if f['properties']['district_type'] != 'congressional']
        districts['features'] = non_cd + features
        
        # Save updated districts
        with open(districts_path, 'w') as f:
            json.dump(districts, f)
        
        print(f"\nUpdated {districts_path}")
        print(f"Total districts: {len(districts['features'])}")
        for feat in districts['features']:
            p = feat['properties']
            plan = p.get('plan', 'original')
            print(f"  {p['district_id']} ({p['district_type']}) - {plan}")

if __name__ == '__main__':
    main()
