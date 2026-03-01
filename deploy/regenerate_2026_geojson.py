#!/usr/bin/env python3
"""Regenerate 2026 GeoJSON files using corrected flip logic and new voter detection from DB."""
import sys
import os
import json

sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')

import database as db

db.init_db()

# Find all 2026 election datasets
conn = db.get_connection()
datasets = conn.execute("""
    SELECT DISTINCT 
        v.county, ve.election_date, ve.party_voted, ve.voting_method
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date LIKE '2026%'
      AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
    ORDER BY ve.election_date, ve.party_voted, ve.voting_method
""").fetchall()

print(f"Found {len(datasets)} 2026 dataset combinations to regenerate")

for row in datasets:
    county = row[0]
    election_date = row[1]
    party = row[2]
    voting_method = row[3]
    
    print(f"\nRegenerating: {county} {election_date} {party} {voting_method}")
    
    geojson = db.generate_geojson_for_election(
        county=county,
        election_date=election_date,
        party=party,
        voting_method=voting_method
    )
    
    features = geojson.get('features', [])
    flipped = sum(1 for f in features if f.get('properties', {}).get('has_switched_parties'))
    new_voters = sum(1 for f in features if f.get('properties', {}).get('is_new_voter'))
    geocoded = sum(1 for f in features if f.get('geometry') is not None)
    
    print(f"  {len(features)} voters, {geocoded} geocoded, {flipped} flipped, {new_voters} new")
    
    # Build filename matching the existing convention
    date_str = election_date.replace('-', '')
    party_lower = party.lower() if party else ''
    if party_lower == 'democratic':
        party_suffix = '_democratic'
    elif party_lower == 'republican':
        party_suffix = '_republican'
    else:
        party_suffix = f'_{party_lower}' if party_lower else ''
    
    method_suffix = '_ev' if 'early' in (voting_method or '').lower() else '_ed'
    
    map_filename = f'map_data_{county}_2026_primary{party_suffix}_{date_str}{method_suffix}.json'
    meta_filename = f'metadata_{county}_2026_primary{party_suffix}_{date_str}{method_suffix}.json'
    
    data_dir = '/opt/whovoted/data'
    
    # Write GeoJSON
    map_path = os.path.join(data_dir, map_filename)
    with open(map_path, 'w') as f:
        json.dump(geojson, f, indent=2)
    print(f"  Wrote {map_path}")
    
    # Update metadata
    meta_path = os.path.join(data_dir, meta_filename)
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)
    else:
        meta = {}
    
    meta['matched_vuids'] = geocoded
    meta['unmatched_vuids'] = len(features) - geocoded
    meta['total_addresses'] = len(features)
    meta['flipped_voters'] = flipped
    meta['new_voters'] = new_voters
    meta['flip_logic'] = 'immediate_predecessor_only'
    
    from datetime import datetime
    meta['last_updated'] = datetime.now().isoformat()
    
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    print(f"  Updated {meta_path}")

    # Also copy to public/data directory (nginx serves from here)
    public_data_dir = '/opt/whovoted/public/data'
    if os.path.exists(public_data_dir):
        public_map = os.path.join(public_data_dir, map_filename)
        with open(public_map, 'w') as f:
            json.dump(geojson, f, indent=2)
        public_meta = os.path.join(public_data_dir, meta_filename)
        with open(public_meta, 'w') as f:
            json.dump(meta, f, indent=2)
        print(f"  Deployed to {public_data_dir}")

print("\nDone! All 2026 GeoJSON files regenerated with corrected flip logic and new voter flags.")
