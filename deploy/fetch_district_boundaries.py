#!/usr/bin/env python3
"""Fetch ALL district boundaries from Census TIGERweb REST API.

Downloads ALL Congressional Districts and ALL TX State House Districts
that intersect Hidalgo County bounding box, and saves as GeoJSON
for the campaigns feature.
"""
import json
import urllib.request
import urllib.parse
import sys

# TIGERweb REST API base
BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services"

# Hidalgo County bounding box (generous)
HIDALGO_BBOX = "-98.8,25.8,-97.4,26.9"

# Distinct colors for districts
CD_COLORS = ['#DC143C', '#FF6347', '#FF8C00', '#B22222', '#CD5C5C', '#E74C3C', '#D35400', '#C0392B']
HD_COLORS = ['#1E90FF', '#4169E1', '#6495ED', '#00BFFF', '#1ABC9C', '#2980B9', '#3498DB', '#5DADE2',
             '#48C9B0', '#1F618D', '#2E86C1', '#21618C', '#2874A6', '#154360']


def fetch_geojson(service_path, layer_id, where_clause, out_fields="*"):
    """Query TIGERweb REST API and return GeoJSON."""
    url = f"{BASE}/{service_path}/MapServer/{layer_id}/query"
    params = {
        "where": where_clause,
        "outFields": out_fields,
        "returnGeometry": "true",
        "f": "geojson",
        "outSR": "4326",
        "geometryType": "esriGeometryEnvelope",
        "geometry": HIDALGO_BBOX,
        "inSR": "4326",
        "spatialRel": "esriSpatialRelIntersects"
    }
    full_url = url + "?" + urllib.parse.urlencode(params)
    print(f"Fetching: {full_url[:120]}...")

    req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())

    if "error" in data:
        print(f"  API Error: {data['error']}")
        return None

    features = data.get("features", [])
    print(f"  Got {len(features)} features")
    return data


def try_services():
    """Try multiple service paths to find ALL district boundaries."""

    cd_features = []
    hd_features = []

    services_to_try = [
        ("TIGERweb/Legislative", "TIGERweb Legislative"),
        ("Generalized_ACS2024/Legislative", "ACS 2024 Legislative"),
        ("Generalized_ACS2023/Legislative", "ACS 2023 Legislative"),
    ]

    for svc, label in services_to_try:
        print(f"\n--- Trying {label}: {svc} ---")
        list_url = f"{BASE}/{svc}/MapServer?f=json"
        try:
            req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                svc_info = json.loads(resp.read().decode())
            layers = svc_info.get("layers", [])
            for layer in layers:
                print(f"  Layer {layer['id']}: {layer['name']}")
        except Exception as e:
            print(f"  Failed to list layers: {e}")
            continue

        # Find Congressional Districts and State House layers
        cd_layer = None
        sldl_layer = None
        for layer in layers:
            name = layer["name"].lower()
            if "congressional" in name:
                if "119" in layer["name"] or cd_layer is None:
                    cd_layer = layer["id"]
            if "state legislative" in name and "lower" in name:
                if "2024" in layer["name"] or sldl_layer is None:
                    sldl_layer = layer["id"]

        # Fetch ALL Congressional Districts in Texas intersecting Hidalgo bbox
        if cd_layer is not None and not cd_features:
            print(f"\n  Querying ALL Congressional Districts (layer {cd_layer})...")
            for where in ["STATEFP='48'", "STATE='48'", "1=1"]:
                try:
                    data = fetch_geojson(svc, cd_layer, where)
                    if data and data.get("features"):
                        # Filter to Texas only if we used 1=1
                        feats = data["features"]
                        if where == "1=1":
                            feats = [f for f in feats
                                     if str(f.get("properties", {}).get("STATEFP", "")) == "48"
                                     or str(f.get("properties", {}).get("STATE", "")) == "48"]
                        if feats:
                            cd_features = feats
                            print(f"  SUCCESS: Got {len(feats)} Congressional Districts with where={where}")
                            break
                except Exception as e:
                    print(f"  Failed with where={where}: {e}")

        # Fetch ALL State House Districts in Texas intersecting Hidalgo bbox
        if sldl_layer is not None and not hd_features:
            print(f"\n  Querying ALL State House Districts (layer {sldl_layer})...")
            for where in ["STATEFP='48'", "STATE='48'", "1=1"]:
                try:
                    data = fetch_geojson(svc, sldl_layer, where)
                    if data and data.get("features"):
                        feats = data["features"]
                        if where == "1=1":
                            feats = [f for f in feats
                                     if str(f.get("properties", {}).get("STATEFP", "")) == "48"
                                     or str(f.get("properties", {}).get("STATE", "")) == "48"]
                        if feats:
                            hd_features = feats
                            print(f"  SUCCESS: Got {len(feats)} State House Districts with where={where}")
                            break
                except Exception as e:
                    print(f"  Failed with where={where}: {e}")

        if cd_features and hd_features:
            break

    return cd_features, hd_features


def get_district_number(props):
    """Extract district number from feature properties."""
    for key in ['BASENAME', 'CD119FP', 'CDFP', 'SLDLST', 'NAME']:
        val = str(props.get(key, '')).strip().lstrip('0')
        if val and val.isdigit():
            return val
    # Try GEOID last 2-3 digits
    geoid = str(props.get('GEOID', ''))
    if geoid.startswith('48') and len(geoid) >= 4:
        return geoid[2:].lstrip('0')
    return None


def main():
    output_dir = "/opt/whovoted/public/data" if len(sys.argv) < 2 else sys.argv[1]

    print("Fetching ALL district boundaries from Census TIGERweb API...")
    cd_features, hd_features = try_services()

    districts = {
        "type": "FeatureCollection",
        "features": []
    }

    # Process Congressional Districts
    if cd_features:
        cd_features.sort(key=lambda f: get_district_number(f.get("properties", {})) or "999")
        for i, f in enumerate(cd_features):
            num = get_district_number(f.get("properties", {}))
            if not num:
                continue
            f["properties"]["district_type"] = "congressional"
            f["properties"]["district_id"] = f"TX-{num}"
            f["properties"]["district_name"] = f"TX-{num} Congressional District"
            f["properties"]["color"] = CD_COLORS[i % len(CD_COLORS)]
            districts["features"].append(f)
        print(f"\nCongressional Districts: {len([f for f in districts['features'] if f['properties']['district_type'] == 'congressional'])}")
    else:
        print("\nWARNING: Could not fetch Congressional District boundaries")

    # Process State House Districts
    if hd_features:
        hd_features.sort(key=lambda f: get_district_number(f.get("properties", {})) or "999")
        for i, f in enumerate(hd_features):
            num = get_district_number(f.get("properties", {}))
            if not num:
                continue
            f["properties"]["district_type"] = "state_house"
            f["properties"]["district_id"] = f"HD-{num}"
            f["properties"]["district_name"] = f"TX State House District {num}"
            f["properties"]["color"] = HD_COLORS[i % len(HD_COLORS)]
            districts["features"].append(f)
        print(f"State House Districts: {len([f for f in districts['features'] if f['properties']['district_type'] == 'state_house'])}")
    else:
        print("WARNING: Could not fetch State House District boundaries")

    # Save
    outpath = f"{output_dir}/districts.json"
    with open(outpath, "w") as f:
        json.dump(districts, f)
    print(f"\nSaved {len(districts['features'])} total district boundaries to {outpath}")
    print(f"File size: {len(json.dumps(districts)) / 1024:.1f} KB")

    # List all districts
    print("\nDistricts found:")
    for f in districts["features"]:
        p = f["properties"]
        print(f"  {p['district_id']} ({p['district_type']}) - {p['color']}")


if __name__ == "__main__":
    main()
