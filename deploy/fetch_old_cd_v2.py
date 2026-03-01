#!/usr/bin/env python3
"""Fetch old congressional boundaries (118th Congress / PlanC2193) from TIGERweb."""
import json
import urllib.request
import urllib.parse

BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services"
HIDALGO_BBOX = "-98.8,25.8,-97.4,26.9"

# First list all layers to find 118th Congress
svc = "TIGERweb/Legislative"
list_url = f"{BASE}/{svc}/MapServer?f=json"
req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=15) as resp:
    svc_info = json.loads(resp.read().decode())

print("All layers:")
for layer in svc_info.get("layers", []):
    print(f"  {layer['id']}: {layer['name']}")

# Try each congressional layer
for layer in svc_info.get("layers", []):
    name = layer["name"]
    if "congressional" not in name.lower():
        continue
    lid = layer["id"]
    print(f"\nTrying layer {lid}: {name}")
    
    url = f"{BASE}/{svc}/MapServer/{lid}/query"
    params = {
        "where": "STATE='48'",
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
    req = urllib.request.Request(full_url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode())
        feats = data.get("features", [])
        print(f"  Got {len(feats)} features")
        for f in feats:
            p = f.get("properties", {})
            # Print all property keys and values
            print(f"    Props: {dict(list(p.items())[:6])}")
    except Exception as e:
        print(f"  Error: {e}")
