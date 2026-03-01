#!/usr/bin/env python3
"""Check what properties exist in the deployed cumulative GeoJSON files."""
import json

for party in ['democratic', 'republican']:
    path = f'/opt/whovoted/data/map_data_Hidalgo_2026_primary_{party}_cumulative_ev.json'
    try:
        with open(path) as f:
            data = json.load(f)
        features = data.get('features', [])
        print(f"\n=== {party.upper()} ({len(features)} features) ===")
        # Show first 3 features' properties
        for i, feat in enumerate(features[:3]):
            props = feat.get('properties', {})
            print(f"\nFeature {i}:")
            print(f"  vuid: {props.get('vuid', 'MISSING')}")
            print(f"  name: '{props.get('name', 'MISSING')}'")
            print(f"  firstname: '{props.get('firstname', 'MISSING')}'")
            print(f"  lastname: '{props.get('lastname', 'MISSING')}'")
            print(f"  sex: '{props.get('sex', 'MISSING')}'")
            print(f"  birth_year: {props.get('birth_year', 'MISSING')}")
            print(f"  precinct: '{props.get('precinct', 'MISSING')}'")
            print(f"  party_affiliation_current: '{props.get('party_affiliation_current', 'MISSING')}'")
        # Count how many have empty names
        empty_names = sum(1 for f in features if not f.get('properties', {}).get('name', '').strip())
        print(f"\nEmpty names: {empty_names} / {len(features)}")
    except Exception as e:
        print(f"Error reading {party}: {e}")
