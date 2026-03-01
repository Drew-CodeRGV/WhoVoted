#!/usr/bin/env python3
import json

with open('/opt/whovoted/public/data/map_data_Hidalgo_2016_primary_democratic_20160301_ev.json') as f:
    data = json.load(f)

features = data.get('features', [])
total = len(features)
has_coords = 0
null_coords = 0
zero_coords = 0

for f in features:
    coords = f.get('geometry', {}).get('coordinates', [None, None])
    if coords and coords[0] is not None and coords[1] is not None:
        if coords[0] == 0 and coords[1] == 0:
            zero_coords += 1
        else:
            has_coords += 1
    else:
        null_coords += 1

print(f"Total features: {total:,}")
print(f"With valid coords: {has_coords:,}")
print(f"Null coords: {null_coords:,}")
print(f"Zero coords (0,0): {zero_coords:,}")
print(f"Unmatched (null+zero): {null_coords + zero_coords:,}")

# Check for unmatched property
unmatched_prop = sum(1 for f in features if f.get('properties', {}).get('unmatched'))
print(f"unmatched=True property: {unmatched_prop:,}")
