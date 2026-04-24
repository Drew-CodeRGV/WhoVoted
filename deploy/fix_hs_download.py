#!/usr/bin/env python3
import requests, json
url = 'https://gismap.mcallen.net/publication/rest/services/SchoolInfoViewer/MapServer/4/query'
names = ['MCALLEN HS', 'MEMORIAL HS', 'NIKKI ROWE HS']
where = ' OR '.join(["NAME = '" + n + "'" for n in names])
params = {'where': where, 'outFields': 'NAME', 'returnGeometry': 'true', 'outSR': '4326', 'f': 'geojson'}
resp = requests.get(url, params=params, timeout=30)
data = resp.json()
print(f"Features: {len(data.get('features', []))}")
for f in data.get('features', []):
    print(f"  {f['properties']['NAME']}")
with open('/opt/whovoted/public/data/mcallen_hs_zones.json', 'w') as fout:
    json.dump(data, fout, separators=(',', ':'))
print("Saved")
