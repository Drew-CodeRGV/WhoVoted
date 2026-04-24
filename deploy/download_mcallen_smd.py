#!/usr/bin/env python3
"""Download McAllen Single Member District boundaries from city ArcGIS server."""
import requests, json

URL = 'https://gismap.mcallen.net/publication/rest/services/SingleMemberDistrict/MapServer/2/query'
params = {
    'where': '1=1',
    'outFields': 'DISTRICTID,NAME,REPNAME',
    'returnGeometry': 'true',
    'outSR': '4326',  # WGS84
    'f': 'geojson'
}

print("Downloading McAllen SMD boundaries...")
resp = requests.get(URL, params=params, timeout=30)
resp.raise_for_status()
data = resp.json()

print(f"Features: {len(data.get('features', []))}")
for f in data.get('features', []):
    props = f.get('properties', {})
    geom = f.get('geometry', {})
    coords = geom.get('coordinates', [[]])
    n_points = sum(len(ring) for ring in coords) if geom.get('type') == 'Polygon' else sum(len(ring) for poly in coords for ring in poly)
    print(f"  {props.get('NAME')}: {props.get('REPNAME')} ({n_points} points)")

# Save
out_path = '/opt/whovoted/public/data/mcallen_smd.json'
with open(out_path, 'w') as f:
    json.dump(data, f, separators=(',', ':'))
print(f"Saved to {out_path}")
