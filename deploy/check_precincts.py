#!/usr/bin/env python3
"""Check what precincts exist in the combined boundaries file."""
import json

path = '/opt/whovoted/public/data/precinct_boundaries_combined.json'
try:
    with open(path) as f:
        data = json.load(f)
    feats = data.get('features', [])
    print(f"Total features: {len(feats)}")
    if feats:
        print(f"Sample properties keys: {list(feats[0].get('properties', {}).keys())}")
        for f in feats[:5]:
            print(f"  Props: {f.get('properties', {})}")
    # Also check the individual files
    for fn in ['precinct_boundaries.json', 'precinct_boundaries_cameron.json']:
        fp = f'/opt/whovoted/public/data/{fn}'
        try:
            with open(fp) as ff:
                d = json.load(ff)
            fs = d.get('features', [])
            print(f"\n{fn}: {len(fs)} features")
            if fs:
                print(f"  Sample: {fs[0].get('properties', {})}")
        except Exception as e:
            print(f"\n{fn}: {e}")
except Exception as e:
    print(f"Error: {e}")
