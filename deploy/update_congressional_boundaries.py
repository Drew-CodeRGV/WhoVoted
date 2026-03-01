#!/usr/bin/env python3
"""Update congressional district boundaries to PlanC2333 (2025 redistricting).

Downloads the new PlanC2333 shapefile from the Texas Capitol Data Portal,
converts to GeoJSON, and updates districts.json with the new boundaries.
Also saves the old boundaries for comparison analysis.

Requires: pip install pyshp (shapefile library)
"""
import json
import os
import sys
import tempfile
import urllib.request
import zipfile

# Try to import shapefile; install if missing
try:
    import shapefile
except ImportError:
    print("Installing pyshp...")
    os.system(f"{sys.executable} -m pip install pyshp")
    import shapefile

# Hidalgo County bounding box for filtering
HIDALGO_BBOX = {
    'min_lng': -98.8, 'max_lng': -97.4,
    'min_lat': 25.8, 'max_lat': 26.9
}

CD_COLORS = {
    '15': '#DC143C',
    '28': '#FF6347',
    '34': '#FF8C00',
    '27': '#B22222',
    '21': '#CD5C5C',
}

def bbox_intersects(coords, bbox):
    """Check if any coordinate in a polygon ring falls within the bounding box."""
    for lng, lat in coords:
        if (bbox['min_lng'] <= lng <= bbox['max_lng'] and
            bbox['min_lat'] <= lat <= bbox['max_lat']):
            return True
    return False

def feature_intersects_bbox(geom, bbox):
    """Check if a GeoJSON geometry intersects the bounding box."""
    if geom['type'] == 'Polygon':
        return any(bbox_intersects(ring, bbox) for ring in geom['coordinates'])
    elif geom['type'] == 'MultiPolygon':
        return any(bbox_intersects(ring, bbox) for poly in geom['coordinates'] for ring in poly)
    return False

def shapefile_to_geojson(shp_path):
    """Convert shapefile to GeoJSON features."""
    sf = shapefile.Reader(shp_path)
    features = []
    for sr in sf.shapeRecords():
        geom = sr.shape.__geo_interface__
        props = {}
        for i, field in enumerate(sf.fields[1:]):  # skip DeletionFlag
            props[field[0]] = sr.record[i]
        features.append({
            'type': 'Feature',
            'geometry': geom,
            'properties': props
        })
    return features

def download_and_extract(url, extract_dir):
    """Download a zip file and extract it."""
    print(f"Downloading {url}...")
    zip_path = os.path.join(extract_dir, 'download.zip')
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible)'})
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(zip_path, 'wb') as f:
            f.write(resp.read())
    print(f"Extracting to {extract_dir}...")
    with zipfile.ZipFile(zip_path, 'r') as z:
        z.extractall(extract_dir)
    os.remove(zip_path)
    # Find .shp file (may be in subdirectory)
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            if f.lower().endswith('.shp'):
                return os.path.join(root, f)
    # List what we got
    for root, dirs, files in os.walk(extract_dir):
        for f in files:
            print(f"  Extracted: {os.path.join(root, f)}")
    return None

def main():
    data_dir = '/opt/whovoted/public/data' if len(sys.argv) < 2 else sys.argv[1]
    districts_path = os.path.join(data_dir, 'districts.json')

    # Load existing districts
    with open(districts_path) as f:
        districts = json.load(f)

    # Save old congressional boundaries for comparison
    old_cd_features = [feat for feat in districts['features']
                       if feat['properties']['district_type'] == 'congressional']
    old_cd_path = os.path.join(data_dir, 'districts_old_congressional.json')
    with open(old_cd_path, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': old_cd_features}, f)
    print(f"Saved {len(old_cd_features)} old congressional boundaries to {old_cd_path}")

    # Download new PlanC2333 shapefile (actual CKAN resource URL)
    plan_url = 'https://data.capitol.texas.gov/dataset/748c952b-e926-4f44-8d01-a738884b3ec8/resource/5712ebe1-d777-4d4a-b836-0534e17bca01/download/planc2333.zip'
    with tempfile.TemporaryDirectory() as tmpdir:
        shp_path = download_and_extract(plan_url, tmpdir)
        if not shp_path:
            print("ERROR: Could not find .shp file in downloaded archive")
            sys.exit(1)

        print(f"Reading shapefile: {shp_path}")
        all_features = shapefile_to_geojson(shp_path)
        print(f"Total features in shapefile: {len(all_features)}")

        # Filter to districts that intersect Hidalgo County
        hidalgo_features = []
        for feat in all_features:
            if feature_intersects_bbox(feat['geometry'], HIDALGO_BBOX):
                hidalgo_features.append(feat)

        print(f"Districts intersecting Hidalgo County: {len(hidalgo_features)}")
        for feat in hidalgo_features:
            props = feat['properties']
            print(f"  District: {props}")

    # Build new congressional features
    new_cd_features = []
    for feat in hidalgo_features:
        props = feat['properties']
        # Extract district number from properties
        dist_num = None
        for key in ['DISTRICT', 'District', 'CD', 'CONG_DIST', 'NAME', 'BASENAME']:
            val = props.get(key)
            if val is not None:
                val_str = str(val).strip().lstrip('0')
                if val_str.isdigit():
                    dist_num = val_str
                    break
        if not dist_num:
            # Try all numeric fields
            for key, val in props.items():
                val_str = str(val).strip().lstrip('0')
                if val_str.isdigit() and 10 <= int(val_str) <= 40:
                    dist_num = val_str
                    break

        if not dist_num:
            print(f"  WARNING: Could not determine district number from {props}")
            continue

        color = CD_COLORS.get(dist_num, '#DC143C')
        new_feat = {
            'type': 'Feature',
            'geometry': feat['geometry'],
            'properties': {
                'district_type': 'congressional',
                'district_id': f'TX-{dist_num}',
                'district_name': f'TX-{dist_num} Congressional District',
                'color': color,
                'plan': 'PlanC2333',
                'redistricted': True
            }
        }
        new_cd_features.append(new_feat)
        print(f"  Added TX-{dist_num} (PlanC2333)")

    # Replace congressional features in districts.json
    non_cd_features = [feat for feat in districts['features']
                       if feat['properties']['district_type'] != 'congressional']
    districts['features'] = non_cd_features + new_cd_features

    # Save updated districts
    with open(districts_path, 'w') as f:
        json.dump(districts, f)
    print(f"\nUpdated {districts_path} with {len(new_cd_features)} new congressional districts")
    print(f"Total districts: {len(districts['features'])}")

    # List all districts
    for feat in districts['features']:
        p = feat['properties']
        plan = p.get('plan', 'original')
        print(f"  {p['district_id']} ({p['district_type']}) - {plan}")

if __name__ == '__main__':
    main()
