#!/usr/bin/env python3
"""Fix DEM cumulative metadata to show raw voter count of 31,905."""
import json

for base_dir in ['/opt/whovoted/data', '/opt/whovoted/public/data']:
    meta_path = f'{base_dir}/metadata_Hidalgo_2026_primary_democratic_cumulative_ev.json'
    try:
        with open(meta_path) as f:
            meta = json.load(f)
        
        old_total = meta.get('total_addresses', 0)
        meta['total_addresses'] = 31905
        meta['raw_voter_count'] = 31905
        
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)
        
        print(f"Updated {meta_path}: total_addresses {old_total} -> 31905")
    except Exception as e:
        print(f"Error updating {meta_path}: {e}")

# Also update REP to include raw_voter_count field
for base_dir in ['/opt/whovoted/data', '/opt/whovoted/public/data']:
    meta_path = f'{base_dir}/metadata_Hidalgo_2026_primary_republican_cumulative_ev.json'
    try:
        with open(meta_path) as f:
            meta = json.load(f)
        
        meta['raw_voter_count'] = meta.get('total_addresses', 7719)
        
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)
        
        print(f"Updated {meta_path}: added raw_voter_count={meta['raw_voter_count']}")
    except Exception as e:
        print(f"Error updating {meta_path}: {e}")

# Also fix day snapshot metadata if it exists
for base_dir in ['/opt/whovoted/data']:
    meta_path = f'{base_dir}/metadata_Hidalgo_2026_primary_democratic_20260303_ev.json'
    try:
        with open(meta_path) as f:
            meta = json.load(f)
        
        meta['raw_voter_count'] = 31905
        
        with open(meta_path, 'w') as f:
            json.dump(meta, f, indent=2)
        
        print(f"Updated {meta_path}: added raw_voter_count=31905")
    except Exception as e:
        print(f"Skipping {meta_path}: {e}")

print("Done.")
