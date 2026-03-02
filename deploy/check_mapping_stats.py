#!/usr/bin/env python3
import json

with open('/opt/whovoted/public/cache/precinct_district_mapping.json') as f:
    mapping = json.load(f)

print(f"Districts mapped: {len(mapping)}")
total_precincts = sum(v['precinct_count'] for v in mapping.values())
print(f"Total precinct mappings: {total_precincts}")

print("\nDistrict breakdown:")
for name, data in mapping.items():
    print(f"  {name:40s} {data['precinct_count']:4d} precincts")

# Check unique precincts
all_precincts = set()
for data in mapping.values():
    all_precincts.update(data['precincts'])

print(f"\nUnique precincts mapped: {len(all_precincts)}")
