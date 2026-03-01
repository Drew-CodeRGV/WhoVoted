#!/usr/bin/env python3
"""Regenerate ALL election GeoJSON files with corrected flip logic and is_new_voter flag."""
import sys
import os
import json

sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')

import database as db

db.init_db()

conn = db.get_connection()

# Find ALL election dataset combinations
datasets = conn.execute("""
    SELECT DISTINCT 
        v.county, ve.election_date, ve.party_voted, ve.voting_method
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.party_voted != '' AND ve.party_voted IS NOT NULL
    ORDER BY ve.election_date, ve.party_voted, ve.voting_method
""").fetchall()

print(f"Found {len(datasets)} dataset combinations to regenerate")

data_dir = '/opt/whovoted/data'
public_data_dir = '/opt/whovoted/public/data'

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
    
    # Derive year from election_date
    year = election_date[:4]
    date_str = election_date.replace('-', '')
    
    party_lower = party.lower() if party else ''
    if party_lower == 'democratic':
        party_suffix = '_democratic'
    elif party_lower == 'republican':
        party_suffix = '_republican'
    else:
        party_suffix = f'_{party_lower}' if party_lower else ''
    
    method_suffix = '_ev' if 'early' in (voting_method or '').lower() else '_ed'
    
    map_filename = f'map_data_{county}_{year}_primary{party_suffix}_{date_str}{method_suffix}.json'
    meta_filename = f'metadata_{county}_{year}_primary{party_suffix}_{date_str}{method_suffix}.json'
    
    # Write to data dir
    map_path = os.path.join(data_dir, map_filename)
    with open(map_path, 'w') as f:
        json.dump(geojson, f, indent=2)
    
    # Update metadata
    meta_path = os.path.join(data_dir, meta_filename)
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)
    else:
        meta = {
            'year': year,
            'county': county,
            'election_type': 'primary',
            'election_date': election_date,
            'voting_method': voting_method,
            'primary_party': party_lower,
        }
    
    meta['matched_vuids'] = geocoded
    meta['unmatched_vuids'] = len(features) - geocoded
    meta['total_addresses'] = len(features)
    meta['successfully_geocoded'] = geocoded
    meta['failed_addresses'] = len(features) - geocoded
    meta['flipped_voters'] = flipped
    meta['new_voters'] = new_voters
    meta['flip_logic'] = 'immediate_predecessor_only'
    
    from datetime import datetime
    meta['last_updated'] = datetime.now().isoformat()
    
    with open(meta_path, 'w') as f:
        json.dump(meta, f, indent=2)
    
    # Deploy to public/data (where nginx serves from)
    if os.path.exists(public_data_dir):
        with open(os.path.join(public_data_dir, map_filename), 'w') as f:
            json.dump(geojson, f, indent=2)
        with open(os.path.join(public_data_dir, meta_filename), 'w') as f:
            json.dump(meta, f, indent=2)
    
    print(f"  Written to data/ and public/data/")

print("\nDone! All GeoJSON files regenerated with is_new_voter and corrected flip logic.")
