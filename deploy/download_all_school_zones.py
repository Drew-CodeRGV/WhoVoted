#!/usr/bin/env python3
"""Download high school and elementary school zone boundaries from McAllen GIS."""
import requests, json

BASE = 'https://gismap.mcallen.net/publication/rest/services/SchoolInfoViewer/MapServer'

# Layer 4 = High, Layer 5 = Elementary
for layer_id, label in [(4, 'High'), (5, 'Elementary')]:
    url = f'{BASE}/{layer_id}/query'
    # First get all names
    params = {'where': '1=1', 'outFields': 'NAME', 'returnGeometry': 'false', 'f': 'json'}
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    names = [f['attributes']['NAME'] for f in data.get('features', [])]
    print(f"\n{label} schools (layer {layer_id}): {len(names)}")
    for n in sorted(names):
        print(f"  {n}")

# Download high school zones (McAllen ISD only)
# Note: Lincoln MS was renamed to Early Achieve HS
MCALLEN_HS = ['MCALLEN HS', 'MEMORIAL HS', 'NIKKI ROWE HS', 'LAMAR ACADEMY']
# Also grab Lincoln MS zone from layer 6 (MS) and rename it for HS
LINCOLN_AS_HS = True
where_hs = ' OR '.join(f"NAME = '{n}'" for n in MCALLEN_HS)
params = {'where': where_hs, 'outFields': 'NAME', 'returnGeometry': 'true', 'outSR': '4326', 'f': 'geojson'}
resp = requests.get(f'{BASE}/4/query', params=params, timeout=30)
hs_data = resp.json()
print(f"\nDownloaded {len(hs_data.get('features', []))} HS zones")
for f in hs_data.get('features', []):
    print(f"  {f['properties']['NAME']}")

# Add Lincoln MS zone (now Early Achieve HS) from MS layer
if LINCOLN_AS_HS:
    lincoln_params = {'where': "NAME = 'LINCOLN MS'", 'outFields': 'NAME', 'returnGeometry': 'true', 'outSR': '4326', 'f': 'geojson'}
    lincoln_resp = requests.get(f'{BASE}/6/query', params=lincoln_params, timeout=30)
    lincoln_data = lincoln_resp.json()
    for feat in lincoln_data.get('features', []):
        feat['properties']['NAME'] = 'EARLY ACHIEVE HS'
        hs_data['features'].append(feat)
        print(f"  Added EARLY ACHIEVE HS (was LINCOLN MS)")

with open('/opt/whovoted/public/data/mcallen_hs_zones.json', 'w') as f:
    json.dump(hs_data, f, separators=(',', ':'))

# Download elementary zones (McAllen ISD only - filter by known names)
# First get all, then we'll filter
params = {'where': '1=1', 'outFields': 'NAME', 'returnGeometry': 'true', 'outSR': '4326', 'f': 'geojson'}
resp = requests.get(f'{BASE}/5/query', params=params, timeout=30)
elem_data = resp.json()
# Filter to McAllen ISD elementary schools
MCALLEN_ELEM_KEYWORDS = ['ALVAREZ', 'BONHAM', 'CAMPOS', 'CASTANEDA', 'CROCKETT', 
    'DE LEON', 'ESCANDON', 'GARZA', 'GONZALEZ', 'HENDRICKS', 'HOUSTON',
    'JACKSON', 'MCAULIFFE', 'MILAM', 'NAVARRO', 'PEREZ', 'RAYBURN',
    'ROOSEVELT', 'SANCHEZ', 'SEGUIN', 'THIGPEN', 'WILSON']
mcallen_elem = {'type': 'FeatureCollection', 'features': []}
for f in elem_data.get('features', []):
    name = f['properties']['NAME']
    if any(kw in name.upper() for kw in MCALLEN_ELEM_KEYWORDS):
        mcallen_elem['features'].append(f)
print(f"\nFiltered {len(mcallen_elem['features'])} McAllen ISD elementary zones")
for f in mcallen_elem['features']:
    print(f"  {f['properties']['NAME']}")
with open('/opt/whovoted/public/data/mcallen_elem_zones.json', 'w') as f:
    json.dump(mcallen_elem, f, separators=(',', ':'))
