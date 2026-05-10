#!/usr/bin/env python3
"""Check what HD-41 boundary data exists."""
import json, os

# Check district reference files
ref_dir = "/opt/whovoted/data/district_reference"
if os.path.exists(ref_dir):
    files = [f for f in os.listdir(ref_dir) if f.endswith(".json")]
    print("JSON files in district_reference:", files)

# Check districts.json
dj = "/opt/whovoted/public/data/districts.json"
if os.path.exists(dj):
    d = json.load(open(dj))
    types = set()
    for f in d.get("features", []):
        props = f.get("properties", {})
        t = props.get("district_type", "unknown")
        types.add(t)
    print(f"districts.json: {len(d.get('features',[]))} features, types: {types}")
    
    # Check for state house
    house = [f for f in d.get("features", []) if "house" in str(f.get("properties", {})).lower()]
    print(f"State house features: {len(house)}")
    if house:
        for h in house[:3]:
            print(f"  Props: {h['properties']}")
else:
    print("districts.json NOT FOUND")

# Check for separate state house file
for path in ["/opt/whovoted/public/data/state_house_districts.json",
             "/opt/whovoted/data/district_reference/state_house_districts.json"]:
    if os.path.exists(path):
        print(f"\nFound: {path}")
        d = json.load(open(path))
        if isinstance(d, dict) and "features" in d:
            print(f"  {len(d['features'])} features")
        elif isinstance(d, list):
            print(f"  {len(d)} items")
            if d:
                print(f"  Sample: {list(d[0].keys()) if isinstance(d[0], dict) else d[0]}")
