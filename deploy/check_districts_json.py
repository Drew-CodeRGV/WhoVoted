#!/usr/bin/env python3
"""Check what's in districts.json"""
import json

with open('/opt/whovoted/public/data/districts.json') as f:
    d = json.load(f)

print(f"Total districts: {len(d['features'])}")

types = {}
for f in d['features']:
    dtype = f['properties']['district_type']
    types[dtype] = types.get(dtype, 0) + 1

print("\nBy type:")
for dtype, count in sorted(types.items()):
    print(f"  {dtype}: {count}")

# Show sample of each type
print("\nSample districts:")
for dtype in sorted(types.keys()):
    samples = [f['properties']['district_id'] for f in d['features'] if f['properties']['district_type'] == dtype][:3]
    print(f"  {dtype}: {', '.join(samples)}")
