#!/usr/bin/env python3
import json

with open('public/data/districts.json') as f:
    data = json.load(f)

print(f'Total features: {len(data["features"])}')
print('\nDistricts:')
for f in data['features']:
    props = f['properties']
    print(f'  {props["district_id"]}: {props["district_name"]}')
