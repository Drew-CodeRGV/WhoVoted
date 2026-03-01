#!/usr/bin/env python3
"""Generate cross-party cumulative EV file by merging DEM + REP cumulative files."""
import json
import os
import shutil
from datetime import datetime

DATA_DIR = '/opt/whovoted/data'
PUBLIC_DIR = '/opt/whovoted/public/data'

county = 'Hidalgo'
year = '2026'
election_type = 'primary'

parties = ['_democratic', '_republican']
all_features = {}

for party_suffix in parties:
    cum_file = os.path.join(DATA_DIR, f'map_data_{county}_{year}_{election_type}{party_suffix}_cumulative_ev.json')
    if not os.path.exists(cum_file):
        print(f"  Not found: {cum_file}")
        continue
    
    with open(cum_file) as f:
        data = json.load(f)
    
    features = data.get('features', [])
    print(f"  {party_suffix}: {len(features)} voters")
    
    for feature in features:
        vuid = feature.get('properties', {}).get('vuid', '')
        if vuid:
            vuid = str(vuid).strip().lstrip('0') or '0'
            all_features[vuid] = feature

features_list = list(all_features.values())
print(f"\nCombined: {len(features_list)} unique voters")

matched = sum(1 for f in features_list if not f.get('properties', {}).get('unmatched', False))
unmatched = sum(1 for f in features_list if f.get('properties', {}).get('unmatched', False))
print(f"  Matched: {matched}, Unmatched: {unmatched}")

# Save combined GeoJSON
combined_data = {'type': 'FeatureCollection', 'features': features_list}
combined_filename = f'map_data_{county}_{year}_{election_type}_cumulative_ev.json'
combined_path = os.path.join(DATA_DIR, combined_filename)
with open(combined_path, 'w') as f:
    json.dump(combined_data, f)
print(f"\nSaved: {combined_filename} ({os.path.getsize(combined_path):,} bytes)")

# Save combined metadata
combined_meta = {
    'year': year,
    'county': county,
    'election_type': election_type,
    'primary_party': '',
    'is_early_voting': True,
    'is_cumulative': True,
    'is_cross_party': True,
    'last_updated': datetime.now().isoformat(),
    'total_addresses': len(features_list),
    'matched_vuids': matched,
    'unmatched_vuids': unmatched,
}
combined_meta_filename = f'metadata_{county}_{year}_{election_type}_cumulative_ev.json'
combined_meta_path = os.path.join(DATA_DIR, combined_meta_filename)
with open(combined_meta_path, 'w') as f:
    json.dump(combined_meta, f, indent=2)

# Deploy to public
os.makedirs(PUBLIC_DIR, exist_ok=True)
for filename in [combined_filename, combined_meta_filename]:
    src = os.path.join(DATA_DIR, filename)
    dst = os.path.join(PUBLIC_DIR, filename)
    shutil.copy2(src, dst)
    print(f"Deployed: {filename}")

print("\nDone!")
