#!/usr/bin/env python3
"""Check which counties are in TX-15 according to the boundary file."""

import json

with open('/opt/whovoted/public/data/districts.json', 'r') as f:
    data = json.load(f)

tx15 = [f for f in data['features'] if f['properties']['district_id'] == 'TX-15'][0]

print("TX-15 Properties:")
print(json.dumps(tx15['properties'], indent=2))
