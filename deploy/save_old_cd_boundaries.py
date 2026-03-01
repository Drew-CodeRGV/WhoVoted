#!/usr/bin/env python3
"""Save 119th Congress (PlanC2193) boundaries as old congressional map for comparison."""
import json
import urllib.request
import urllib.parse

BASE = "https://tigerweb.geo.census.gov/arcgis/rest/services"
HIDALGO_BBOX = "-98.8,25.8,-97.4,26.9"
CD_COLORS = {'15': '#DC143C', '28': '#FF6347', '34': '#FF8C00'}

# Fetch 119th Congress districts (layer 0) - these are the PlanC2193 boundaries
url = f"{BASE}/TIGERweb/Legislative/MapServer/0/query"
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
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode())

features = []
for f in data.get("features", []):
    p = f["properties"]
    num = str(p.get("BASENAME", "")).strip()
    if not num:
        continue
    f["properties"] = {
        "district_type": "congressional",
        "district_id": f"TX-{num}",
        "district_name": f"TX-{num} Congressional District (2022-2024 Map)",
        "color": CD_COLORS.get(num, '#DC143C'),
        "plan": "PlanC2193"
    }
    features.append(f)
    print(f"  Old TX-{num} (119th Congress / PlanC2193)")

outpath = '/opt/whovoted/public/data/districts_old_congressional.json'
with open(outpath, 'w') as fp:
    json.dump({"type": "FeatureCollection", "features": features}, fp)
size_kb = len(json.dumps({"type": "FeatureCollection", "features": features})) / 1024
print(f"\nSaved {len(features)} old congressional boundaries ({size_kb:.0f} KB)")
