#!/usr/bin/env python3
"""Regenerate the 20260224 day-snapshot and cumulative files with newly geocoded data."""
import sys, os, json
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')
import database as db
from datetime import datetime
db.init_db()

data_dir = '/opt/whovoted/data'
public_data_dir = '/opt/whovoted/public/data'

# The processor used election_date from the form (2026-03-03) but roster_date 2026-02-24
# The day-snapshot files use the roster date in the filename
# The cumulative files aggregate all records for that election

# Regenerate using the actual election_date in the DB (2026-03-03)
for party in ['Democratic', 'Republican']:
    print(f"Regenerating {party} cumulative and day-snapshot...")
    
    geojson = db.generate_geojson_for_election(
        county='Hidalgo', election_date='2026-03-03',
        party=party, voting_method='early-voting'
    )
    
    features = geojson.get('features', [])
    geocoded = sum(1 for f in features if f.get('geometry') is not None)
    print(f"  {len(features)} features, {geocoded} geocoded, {len(features)-geocoded} ungeocoded")
    
    party_suffix = '_democratic' if 'democrat' in party.lower() else '_republican'
    
    # Write day-snapshot (20260224)
    day_map = f'map_data_Hidalgo_2026_primary{party_suffix}_20260224_ev.json'
    day_meta = f'metadata_Hidalgo_2026_primary{party_suffix}_20260224_ev.json'
    
    # Write cumulative
    cum_map = f'map_data_Hidalgo_2026_primary{party_suffix}_cumulative_ev.json'
    cum_meta = f'metadata_Hidalgo_2026_primary{party_suffix}_cumulative_ev.json'
    
    for filename in [day_map, cum_map]:
        for d in [data_dir, public_data_dir]:
            path = os.path.join(d, filename)
            if os.path.exists(path) or d == public_data_dir:
                with open(path, 'w') as f:
                    json.dump(geojson, f)
                print(f"  Updated {filename} in {d}")
    
    # Update metadata
    for meta_filename in [day_meta, cum_meta]:
        for d in [data_dir, public_data_dir]:
            meta_path = os.path.join(d, meta_filename)
            if os.path.exists(meta_path):
                with open(meta_path, 'r') as f:
                    meta = json.load(f)
                meta['matched_vuids'] = geocoded
                meta['unmatched_vuids'] = len(features) - geocoded
                meta['total_addresses'] = len(features)
                meta['successfully_geocoded'] = geocoded
                meta['last_updated'] = datetime.now().isoformat()
                with open(meta_path, 'w') as f:
                    json.dump(meta, f, indent=2)
                print(f"  Updated {meta_filename} in {d}")

print("\nDone! All 2026 GeoJSON files should now be fully geocoded.")
