#!/usr/bin/env python3
"""Check current feature counts in deployed GeoJSON files."""
import json

for party in ['democratic', 'republican']:
    path = f'/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_{party}_cumulative_ev.json'
    try:
        with open(path) as f:
            data = json.load(f)
        print(f"{party.upper()} features: {len(data['features'])}")
    except Exception as e:
        print(f"{party.upper()} error: {e}")
