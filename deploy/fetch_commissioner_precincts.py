#!/usr/bin/env python3
"""
Fetch Hidalgo County Commissioner Precinct boundaries from Census TIGERweb API
and add them to the existing districts.json file.

Hidalgo County FIPS: 48215 (state=48, county=215)
"""
import json
import urllib.request
import urllib.parse
import sys

BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services"
HIDALGO_BBOX = "-98.8,25.8,-97.4,26.9"

COLORS = {
    '1': '#e74c3c',
    '2': '#3498db',
    '3': '#2ecc71',
    '4': '#f39c12',
}

def fetch_geojson(service_path, layer_id, where_clause):
    url = f"{BASE}/{service_path}/MapServer/{layer_id}/query"
    params = {
        "where": where_clause,
        "outFields": "*",
        "returnGeometry": "true",
        "f": "geojson",
        "outSR": "4326",
        "geometryType": "esriGeometryEnvelope",
        "geometry": HIDALGO_BBOX,
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects"
    }
    full_url = url + "?" + urllib.parse.urlencode(params)
    print(f"  Fetching: {full_url[:140]}...")
    req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    if "error" in data:
        print(f"  API Error: {data['error']}")
        return None
    features = data.get("features", [])
    print(f"  Got {len(features)} features")
    return data

def list_layers(service_path):
    url = f"{BASE}/{service_path}/MapServer?f=json"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        info = json.loads(resp.read().decode())
    return info.get("layers", [])

def main():
    output_dir = "/opt/whovoted/public/data" if len(sys.argv) < 2 else sys.argv[1]

    print("Searching for County Subdivision layers (Commissioner Precincts)...")

    services = [
        "TIGERweb/tigerWMS_Current",
        "TIGERweb/Tracts_Blocks",
        "TIGERweb/Legislative",
    ]

    cousub_features = []

    for svc in services:
        print(f"\n--- Service: {svc} ---")
        try:
            layers = list_layers(svc)
            for l in layers:
                name = l['name'].lower()
                if 'county sub' in name or 'cousub' in name or 'subdivision' in name:
                    print(f"  Found layer {l['id']}: {l['name']}")
                    for where in ["STATEFP='48' AND COUNTYFP='215'", "STATE='48' AND COUNTY='215'", "1=1"]:
                        try:
                            data = fetch_geojson(svc, l['id'], where)
                            if data and data.get('features'):
                                feats = data['features']
                                if where == "1=1":
                                    feats = [f for f in feats
                                             if str(f.get('properties', {}).get('STATEFP', '')) == '48'
                                             or str(f.get('properties', {}).get('STATE', '')) == '48']
                                if feats:
                                    cousub_features = feats
                                    print(f"  SUCCESS: {len(feats)} features with where={where}")
                                    for ff in feats:
                                        p = ff.get('properties', {})
                                        print(f"    {p.get('NAME', p.get('BASENAME', '?'))} COUSUBFP={p.get('COUSUBFP', '?')}")
                                    break
                        except Exception as e:
                            print(f"    Failed: {e}")
                    if cousub_features:
                        break
        except Exception as e:
            print(f"  Failed to list layers: {e}")
        if cousub_features:
            break

    if not cousub_features:
        print("\nNo county subdivision features found. Trying direct COUSUB query...")
        # Try the direct COUSUB layer (layer 22 in tigerWMS_Current)
        for lid in [20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40]:
            try:
                data = fetch_geojson("TIGERweb/tigerWMS_Current", lid, "STATEFP='48' AND COUNTYFP='215'")
                if data and data.get('features'):
                    cousub_features = data['features']
                    print(f"  Layer {lid}: {len(cousub_features)} features")
                    for ff in cousub_features[:3]:
                        print(f"    {ff.get('properties', {})}")
                    if len(cousub_features) >= 3:
                        break
            except:
                pass

    if not cousub_features:
        print("\nERROR: Could not find commissioner precinct boundaries.")
        print("Listing all layers in tigerWMS_Current for reference:")
        try:
            layers = list_layers("TIGERweb/tigerWMS_Current")
            for l in layers:
                print(f"  {l['id']}: {l['name']}")
        except Exception as e:
            print(f"  {e}")
        sys.exit(1)

    # Load existing districts.json
    districts_path = f"{output_dir}/districts.json"
    try:
        with open(districts_path) as f:
            districts = json.load(f)
    except:
        districts = {"type": "FeatureCollection", "features": []}

    # Remove any existing commissioner features
    districts['features'] = [f for f in districts['features']
                             if f.get('properties', {}).get('district_type') != 'commissioner']

    # Add commissioner precincts
    for feat in cousub_features:
        props = feat.get('properties', {})
        name = props.get('NAME', props.get('BASENAME', ''))
        # Extract precinct number
        pct_num = ''
        for word in name.split():
            if word.isdigit():
                pct_num = word
                break
        if not pct_num:
            # Try COUSUBFP last 2 digits
            fp = str(props.get('COUSUBFP', ''))
            if fp:
                pct_num = str(int(fp[-2:]) if fp[-2:].isdigit() else '')

        feat['properties'] = {
            'district_type': 'commissioner',
            'district_id': f'CPct-{pct_num}',
            'district_name': f'Commissioner Precinct {pct_num}',
            'color': COLORS.get(pct_num, '#999'),
            'name': name,
            'cousubfp': props.get('COUSUBFP', ''),
            'geoid': props.get('GEOID', ''),
        }
        districts['features'].append(feat)

    with open(districts_path, 'w') as f:
        json.dump(districts, f)

    comm_count = len([f for f in districts['features'] if f['properties']['district_type'] == 'commissioner'])
    total = len(districts['features'])
    print(f"\nAdded {comm_count} commissioner precincts to districts.json ({total} total features)")
    print(f"File size: {len(json.dumps(districts)) / 1024:.1f} KB")

if __name__ == "__main__":
    main()
