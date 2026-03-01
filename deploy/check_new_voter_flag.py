#!/usr/bin/env python3
"""Check if is_new_voter flag exists in the served GeoJSON files."""
import json, os, glob

for d in ['/opt/whovoted/public', '/opt/whovoted/data']:
    print(f"\n=== Checking {d} ===")
    for f in sorted(glob.glob(os.path.join(d, 'map_data_*2026*.json'))):
        with open(f) as fh:
            gj = json.load(fh)
        features = gj.get('features', [])
        if not features:
            print(f"  {os.path.basename(f)}: 0 features")
            continue
        has_flag = sum(1 for feat in features if 'is_new_voter' in feat.get('properties', {}))
        new_true = sum(1 for feat in features if feat.get('properties', {}).get('is_new_voter') == True)
        print(f"  {os.path.basename(f)}: {len(features)} features, {has_flag} have is_new_voter field, {new_true} are new")
        # Show first feature's keys
        if features:
            print(f"    Sample keys: {list(features[0].get('properties', {}).keys())}")
