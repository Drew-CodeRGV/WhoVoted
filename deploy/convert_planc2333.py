#!/usr/bin/env python3
"""Convert PlanC2333 shapefile to GeoJSON with WGS84 coordinates.
Filters to districts intersecting Hidalgo County.
Also saves old congressional boundaries for comparison.
"""
import shapefile
import json
import os
import sys

try:
    from pyproj import Transformer
except ImportError:
    os.system(f"{sys.executable} -m pip install pyproj")
    from pyproj import Transformer

SHP_PATH = '/tmp/planc2333/PLANC2333/PLANC2333.shp'
DATA_DIR = '/opt/whovoted/public/data'

# NAD83 Texas State Plane (Lambert Conformal Conic) -> WGS84
# The .prj says NAD_1983_Lambert_Conformal_Conic with False_Easting=1000000
# This is likely EPSG:3082 (Texas Centric Lambert Conformal) or similar
# Let's use the proj string from the .prj file
PRJ_STRING = (
    '+proj=lcc +lat_1=27.41666666666667 +lat_2=34.91666666666666 '
    '+lat_0=31.16666666666667 +lon_0=-100 +x_0=1000000 +y_0=1000000 '
    '+datum=NAD83 +units=ft +no_defs'
)

# Hidalgo County bounding box in WGS84
HIDALGO_BBOX = {'min_lng': -98.8, 'max_lng': -97.4, 'min_lat': 25.8, 'max_lat': 26.9}

CD_COLORS = {
    '15': '#DC143C', '28': '#FF6347', '34': '#FF8C00',
    '27': '#B22222', '21': '#CD5C5C', '16': '#E74C3C',
}

def transform_coords(coords, transformer):
    """Recursively transform coordinates from projected to WGS84."""
    if isinstance(coords[0], (int, float)):
        # Single point [x, y]
        lng, lat = transformer.transform(coords[0], coords[1])
        return [round(lng, 6), round(lat, 6)]
    return [transform_coords(c, transformer) for c in coords]

def bbox_intersects(coords, bbox):
    for c in coords:
        if isinstance(c[0], (int, float)):
            lng, lat = c[0], c[1]
            if bbox['min_lng'] <= lng <= bbox['max_lng'] and bbox['min_lat'] <= lat <= bbox['max_lat']:
                return True
        else:
            if bbox_intersects(c, bbox):
                return True
    return False

def main():
    # Try different projection parameters
    # First try with US feet
    transformers_to_try = [
        ('+proj=lcc +lat_1=27.41666666666667 +lat_2=34.91666666666666 '
         '+lat_0=31.16666666666667 +lon_0=-100 +x_0=1000000 +y_0=1000000 '
         '+datum=NAD83 +units=m +no_defs', 'NAD83 LCC meters'),
        ('+proj=lcc +lat_1=27.41666666666667 +lat_2=34.91666666666666 '
         '+lat_0=31.16666666666667 +lon_0=-100 +x_0=1000000 +y_0=1000000 '
         '+datum=NAD83 +units=us-ft +no_defs', 'NAD83 LCC US feet'),
        ('+proj=lcc +lat_1=27.41666666666667 +lat_2=34.91666666666666 '
         '+lat_0=31.16666666666667 +lon_0=-100 +x_0=1000000 +y_0=1000000 '
         '+datum=NAD83 +units=ft +no_defs', 'NAD83 LCC feet'),
        ('EPSG:3082', 'EPSG:3082 TX Centric Lambert'),
        ('EPSG:3083', 'EPSG:3083 TX Centric Albers'),
        ('EPSG:32139', 'EPSG:32139 TX South Central'),
    ]

    sf = shapefile.Reader(SHP_PATH)
    print(f"Shapefile: {len(sf)} features")
    print(f"Bounding box: {sf.bbox}")

    # Test each projection with a known point
    test_x, test_y = sf.bbox[0], sf.bbox[1]  # lower-left corner
    for proj_str, label in transformers_to_try:
        try:
            t = Transformer.from_crs(proj_str, 'EPSG:4326', always_xy=True)
            lng, lat = t.transform(test_x, test_y)
            print(f"\n{label}: ({test_x:.0f}, {test_y:.0f}) -> ({lng:.4f}, {lat:.4f})")
            # Check if result is in Texas
            if -107 < lng < -93 and 25 < lat < 37:
                print(f"  -> Looks like Texas! Using this projection.")
                transformer = t
                break
        except Exception as e:
            print(f"  {label}: Failed - {e}")
    else:
        print("ERROR: No projection produced Texas coordinates")
        sys.exit(1)

    # Convert all features
    new_features = []
    hidalgo_features = []
    for sr in sf.shapeRecords():
        geom = sr.shape.__geo_interface__
        dist_num = str(sr.record[0]).strip()
        
        # Transform coordinates
        transformed_geom = {
            'type': geom['type'],
            'coordinates': transform_coords(geom['coordinates'], transformer)
        }
        
        feat = {
            'type': 'Feature',
            'geometry': transformed_geom,
            'properties': {'District': dist_num}
        }
        new_features.append(feat)
        
        # Check if intersects Hidalgo County
        if bbox_intersects(transformed_geom['coordinates'], HIDALGO_BBOX):
            hidalgo_features.append(feat)
            print(f"  District {dist_num} intersects Hidalgo County")

    print(f"\nTotal districts: {len(new_features)}")
    print(f"Hidalgo County districts: {len(hidalgo_features)}")

    # Load existing districts.json
    districts_path = os.path.join(DATA_DIR, 'districts.json')
    with open(districts_path) as f:
        districts = json.load(f)

    # Save old congressional boundaries
    old_cd = [feat for feat in districts['features'] if feat['properties']['district_type'] == 'congressional']
    old_path = os.path.join(DATA_DIR, 'districts_old_congressional.json')
    with open(old_path, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': old_cd}, f)
    print(f"Saved {len(old_cd)} old congressional boundaries to {old_path}")

    # Remove old congressional features
    non_cd = [feat for feat in districts['features'] if feat['properties']['district_type'] != 'congressional']

    # Add new congressional features
    for feat in hidalgo_features:
        dist_num = feat['properties']['District']
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
        non_cd.append(new_feat)
        print(f"  Added TX-{dist_num} (PlanC2333)")

    districts['features'] = non_cd
    with open(districts_path, 'w') as f:
        json.dump(districts, f)
    
    size_kb = os.path.getsize(districts_path) / 1024
    print(f"\nUpdated {districts_path} ({size_kb:.0f} KB)")
    print(f"Total districts: {len(districts['features'])}")
    for feat in districts['features']:
        p = feat['properties']
        print(f"  {p['district_id']} ({p['district_type']})")

if __name__ == '__main__':
    main()
