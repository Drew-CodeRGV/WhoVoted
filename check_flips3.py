import json
from pathlib import Path

data_dir = Path('/opt/whovoted/data')

# Check DEM file for R->D flips
with open(data_dir / 'map_data_Hidalgo_2026_primary_democratic_20260223.json') as f:
    data = json.load(f)

features = data.get('features', [])
r_to_d = 0
d_to_r = 0
other_flip = 0
for feat in features:
    p = feat.get('properties', {})
    prev = (p.get('party_affiliation_previous') or '').lower()
    cur = (p.get('party_affiliation_current') or '').lower()
    if not prev:
        continue
    if 'republican' in prev and 'democrat' in cur:
        r_to_d += 1
    elif 'democrat' in prev and 'republican' in cur:
        d_to_r += 1
    else:
        other_flip += 1

print(f"DEM file: R->D={r_to_d}, D->R={d_to_r}, other={other_flip}")

# Check REP file for D->R flips
with open(data_dir / 'map_data_Hidalgo_2026_primary_republican_20260223.json') as f:
    data = json.load(f)

features = data.get('features', [])
r_to_d_rep = 0
d_to_r_rep = 0
other_flip_rep = 0
for feat in features:
    p = feat.get('properties', {})
    prev = (p.get('party_affiliation_previous') or '').lower()
    cur = (p.get('party_affiliation_current') or '').lower()
    if not prev:
        continue
    if 'republican' in prev and 'democrat' in cur:
        r_to_d_rep += 1
    elif 'democrat' in prev and 'republican' in cur:
        d_to_r_rep += 1
    else:
        other_flip_rep += 1

print(f"REP file: R->D={r_to_d_rep}, D->R={d_to_r_rep}, other={other_flip_rep}")
print()
print(f"Total R->D flips: {r_to_d + r_to_d_rep}")
print(f"Total D->R flips: {d_to_r + d_to_r_rep}")
