#!/usr/bin/env python3
"""Check if both cumulative GeoJSON files are valid and accessible."""
import json
import os

for party in ['democratic', 'republican']:
    path = f'/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_{party}_cumulative_ev.json'
    try:
        size = os.path.getsize(path)
        with open(path) as f:
            data = json.load(f)
        features = len(data.get('features', []))
        print(f"{party.upper()}: {features} features, {size:,} bytes, valid JSON")
    except Exception as e:
        print(f"{party.upper()}: ERROR - {e}")

# Also check via HTTP
import urllib.request
for party in ['democratic', 'republican']:
    url = f'http://localhost:5000/data/map_data_Hidalgo_2026_primary_{party}_cumulative_ev.json'
    try:
        resp = urllib.request.urlopen(url)
        data = json.loads(resp.read())
        print(f"{party.upper()} via HTTP: {len(data.get('features', []))} features, status OK")
    except Exception as e:
        print(f"{party.upper()} via HTTP: ERROR - {e}")
