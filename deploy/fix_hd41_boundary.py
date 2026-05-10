#!/usr/bin/env python3
"""
Fix HD-41 boundary by downloading the CURRENT (post-2021 redistricting) boundary.

The existing boundary has LSY=2018 (pre-redistricting). The correct boundary
is from PLANH2316 (2021 redistricting plan, effective 2022).

Strategy:
1. Try Census TIGERweb 2024 layer (should have current boundaries)
2. Try multiple layer IDs since Census changes them
3. Validate the new boundary makes geographic sense for HD-41
   (should cover Weslaco/Mercedes/parts of McAllen area)
"""
import json, urllib.request, sys
from pathlib import Path

DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
BOUNDARY_CACHE = '/opt/whovoted/public/cache/hd41_boundary.json'

# TIGERweb endpoints to try — Census changes layer numbers periodically
ENDPOINTS = [
    # 2024 TIGER/Line current boundaries
    'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/44/query?where=STATE%3D%2748%27+AND+SLDL%3D%27041%27&outFields=*&f=geojson',
    'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/46/query?where=STATE%3D%2748%27+AND+SLDL%3D%27041%27&outFields=*&f=geojson',
    'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/48/query?where=STATE%3D%2748%27+AND+SLDL%3D%27041%27&outFields=*&f=geojson',
    # Legislative layer
    'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/14/query?where=STATE%3D%2748%27+AND+SLDL%3D%27041%27&outFields=*&f=geojson',
    'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/16/query?where=STATE%3D%2748%27+AND+SLDL%3D%27041%27&outFields=*&f=geojson',
    # Try with BASENAME
    'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/14/query?where=STATE%3D%2748%27+AND+BASENAME%3D%2741%27&outFields=*&f=geojson',
    'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/16/query?where=STATE%3D%2748%27+AND+BASENAME%3D%2741%27&outFields=*&f=geojson',
    # 2023 ACS boundaries
    'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2023/MapServer/44/query?where=STATE%3D%2748%27+AND+SLDL%3D%27041%27&outFields=*&f=geojson',
    'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_ACS2023/MapServer/46/query?where=STATE%3D%2748%27+AND+SLDL%3D%27041%27&outFields=*&f=geojson',
]


def fetch_boundary():
    """Try multiple endpoints to get the current HD-41 boundary."""
    for url in ENDPOINTS:
        print(f"  Trying: ...{url.split('MapServer')[1][:60]}")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'WhoVoted/1.0'})
            resp = urllib.request.urlopen(req, timeout=20)
            data = json.loads(resp.read())
            if data.get('features') and len(data['features']) > 0:
                feat = data['features'][0]
                props = feat.get('properties', {})
                lsy = props.get('LSY', 'unknown')
                name = props.get('NAME', props.get('BASENAME', 'unknown'))
                print(f"    ✓ Got: {name}, LSY={lsy}")
                # Only accept if LSY >= 2022 (post-redistricting)
                try:
                    if int(lsy) >= 2022:
                        print(f"    ✓ Post-redistricting boundary (LSY={lsy})")
                        return feat
                    else:
                        print(f"    ✗ Old boundary (LSY={lsy}), skipping...")
                except (ValueError, TypeError):
                    # If LSY is missing, check geometry size
                    geom = feat.get('geometry', {})
                    coords = geom.get('coordinates', [[]])[0] if geom.get('type') == 'Polygon' else geom.get('coordinates', [[[]]])[0][0]
                    if len(coords) > 100:
                        print(f"    ✓ Accepting (no LSY but has {len(coords)} vertices)")
                        return feat
            elif data.get('error'):
                print(f"    Error: {data['error'].get('message', '')[:60]}")
        except Exception as e:
            print(f"    Failed: {str(e)[:60]}")
    return None


def validate_boundary(feature):
    """Check that the boundary makes geographic sense for HD-41."""
    geom = feature['geometry']
    if geom['type'] == 'Polygon':
        coords = geom['coordinates'][0]
    elif geom['type'] == 'MultiPolygon':
        coords = geom['coordinates'][0][0]
    else:
        return False

    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]

    # HD-41 should be in the Hidalgo County area (roughly 26.0-26.4 lat, -98.0 to -98.5 lng)
    center_lat = (min(lats) + max(lats)) / 2
    center_lng = (min(lngs) + max(lngs)) / 2

    if 25.8 < center_lat < 26.6 and -98.6 < center_lng < -97.8:
        print(f"  ✓ Boundary center ({center_lat:.3f}, {center_lng:.3f}) is in Hidalgo County area")
        print(f"  Bbox: lat {min(lats):.4f}-{max(lats):.4f}, lng {min(lngs):.4f}-{max(lngs):.4f}")
        print(f"  Vertices: {len(coords)}")
        return True
    else:
        print(f"  ✗ Boundary center ({center_lat:.3f}, {center_lng:.3f}) is NOT in expected area")
        return False


def update_districts_json(feature):
    """Replace HD-41 in districts.json with the new boundary."""
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)

    # Remove old HD-41
    districts['features'] = [f for f in districts['features'] if f.get('properties', {}).get('district_id') != 'HD-41']

    # Add new with standardized properties
    props = feature.get('properties', {})
    new_feature = {
        'type': 'Feature',
        'properties': {
            'district_type': 'state_house',
            'district_id': 'HD-41',
            'district_name': 'TX State House District 41',
            'NAME': props.get('NAME', 'State House District 41'),
            'BASENAME': '41',
            'SLDL': '041',
            'STATE': '48',
            'LSY': props.get('LSY', '2024'),
            'color': '#FF6347',
        },
        'geometry': feature['geometry']
    }
    districts['features'].append(new_feature)

    with open(DISTRICTS_PATH, 'w') as f:
        json.dump(districts, f)
    print(f"  ✓ Updated districts.json ({len(districts['features'])} features)")

    # Also update the standalone boundary cache
    with open(BOUNDARY_CACHE, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': [new_feature]}, f, separators=(',', ':'))
    print(f"  ✓ Updated hd41_boundary.json ({Path(BOUNDARY_CACHE).stat().st_size/1024:.0f} KB)")


def main():
    print("Fixing HD-41 boundary (current is LSY=2018, need post-2021 redistricting)...\n")

    feature = fetch_boundary()
    if not feature:
        print("\nERROR: Could not download updated boundary from any endpoint.")
        print("Manual fix needed: download from https://dvr.capitol.texas.gov/")
        sys.exit(1)

    print("\nValidating...")
    if not validate_boundary(feature):
        print("ERROR: Downloaded boundary failed validation.")
        sys.exit(1)

    print("\nUpdating files...")
    update_districts_json(feature)
    print("\n✓ Done! HD-41 boundary updated.")
    print("  Next: re-run cache_hd41_precincts_verified.py to re-validate precincts")


if __name__ == '__main__':
    main()
