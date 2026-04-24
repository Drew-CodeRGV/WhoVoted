#!/usr/bin/env python3
"""Download McAllen ISD middle school zone boundaries from city GIS."""
import requests, json

URL = 'https://gismap.mcallen.net/publication/rest/services/SchoolInfoViewer/MapServer/6/query'

# Only McAllen ISD middle schools
# Note: Lincoln MS is now Early Achieve HS - removed from MS list
MCALLEN_ISD_MS = ['CATHAY MS', 'DELEON MS', 'FOSSUM', 'MORRIS MS', 'TRAVIS MS', 'BROWN MS']
where = ' OR '.join(f"NAME = '{n}'" for n in MCALLEN_ISD_MS)

params = {
    'where': where,
    'outFields': 'NAME,POPULATION,STUDENTS,LOTS',
    'returnGeometry': 'true',
    'outSR': '4326',
    'f': 'geojson'
}

print("Downloading McAllen ISD middle school zones...")
resp = requests.get(URL, params=params, timeout=30)
resp.raise_for_status()
data = resp.json()

print(f"Features: {len(data.get('features', []))}")
for f in data.get('features', []):
    p = f.get('properties', {})
    print(f"  {p.get('NAME')}: pop={p.get('POPULATION')}, students={p.get('STUDENTS')}")

out_path = '/opt/whovoted/public/data/mcallen_ms_zones.json'
with open(out_path, 'w') as f:
    json.dump(data, f, separators=(',', ':'))
print(f"Saved to {out_path}")
