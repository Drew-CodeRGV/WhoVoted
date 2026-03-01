#!/usr/bin/env python3
"""Fetch the old (PlanC2193 / 118th Congress) congressional district boundaries
from Census TIGERweb API and save as districts_old_congressional.json."""
import json
import urllib.request
import urllib.parse

BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services"
HIDALGO_BBOX = "-98.8,25.8,-97.4,26.9"

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
    print(f"Fetching: {full_url[:120]}...")
    req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    features = data.get("features", [])
    print(f"  Got {len(features)} features")
    return features

# Try TIGERweb Legislative service
services = [
    ("TIGERweb/Legislative", "TIGERweb Legislative"),
    ("Generalized_ACS2024/Legislative", "ACS 2024"),
    ("Generalized_ACS2023/Legislative", "ACS 2023"),
]

cd_features = []
for svc, label in services:
    print(f"\nTrying {label}...")
    try:
        # List layers
        list_url = f"{BASE}/{svc}/MapServer?f=json"
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            svc_info = json.loads(resp.read().decode())
        layers = svc_info.get("layers", [])
        
        cd_layer = None
        for layer in layers:
            name = layer["name"].lower()
            if "congressional" in name:
                cd_layer = layer["id"]
                print(f"  Found CD layer: {layer['id']} - {layer['name']}")
        
        if cd_layer is not None:
            feats = fetch_geojson(svc, cd_layer, "STATEFP='48'")
            if not feats:
                feats = fetch_geojson(svc, cd_layer, "STATE='48'")
            if not feats:
                feats = fetch_geojson(svc, cd_layer, "1=1")
                feats = [f for f in feats if str(f.get("properties", {}).get("STATEFP", "")) == "48"]
            if feats:
                cd_features = feats
                break
    except Exception as e:
        print(f"  Error: {e}")

if not cd_features:
    print("ERROR: Could not fetch old congressional boundaries")
    exit(1)

# Format features
CD_COLORS = ['#DC143C', '#FF6347', '#FF8C00']
old_features = []
for i, f in enumerate(cd_features):
    props = f.get("properties", {})
    # Extract district number
    num = None
    for key in ['BASENAME', 'CD119FP', 'CDFP', 'NAME']:
        val = str(props.get(key, '')).strip().lstrip('0')
        if val and val.isdigit():
            num = val
            break
    if not num:
        geoid = str(props.get('GEOID', ''))
        if geoid.startswith('48') and len(geoid) >= 4:
            num = geoid[2:].lstrip('0')
    if not num:
        continue
    
    f["properties"] = {
        "district_type": "congressional",
        "district_id": f"TX-{num}",
        "district_name": f"TX-{num} Congressional District (Old Map)",
        "color": CD_COLORS[i % len(CD_COLORS)],
        "plan": "PlanC2193"
    }
    old_features.append(f)
    print(f"  Old TX-{num}")

outpath = '/opt/whovoted/public/data/districts_old_congressional.json'
with open(outpath, 'w') as fp:
    json.dump({"type": "FeatureCollection", "features": old_features}, fp)
print(f"\nSaved {len(old_features)} old congressional boundaries to {outpath}")
