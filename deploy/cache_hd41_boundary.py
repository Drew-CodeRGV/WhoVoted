#!/usr/bin/env python3
"""Extract HD-41 boundary from districts.json into a standalone file for the frontend overlay."""
import json
from pathlib import Path

DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_boundary.json'

def main():
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)

    hd41 = [f for f in districts['features'] if f.get('properties', {}).get('district_id') == 'HD-41']
    if not hd41:
        print("ERROR: HD-41 not found in districts.json")
        return

    feature = hd41[0]
    output = {
        'type': 'FeatureCollection',
        'features': [feature]
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    print(f"✓ HD-41 boundary extracted: {Path(CACHE_PATH).stat().st_size / 1024:.0f} KB")

if __name__ == '__main__':
    main()
