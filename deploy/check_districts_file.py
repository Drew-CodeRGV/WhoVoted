#!/usr/bin/env python3
import json

d = json.load(open('public/data/districts.json'))
print(f'Total features: {len(d["features"])}')
types = {}
for f in d['features']:
    dt = f['properties']['district_type']
    types[dt] = types.get(dt, 0) + 1
print('By type:', types)
print('\nSample districts:')
for f in d['features'][:10]:
    p = f['properties']
    print(f"  {p.get('district_id', 'unknown')}: {p['district_type']}")
