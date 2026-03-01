#!/usr/bin/env python3
"""Geocode voters who have addresses but no coordinates in the DB,
then regenerate the 2026 GeoJSON files so they appear on the map."""
import sys
import os
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')

import database as db
from geocoder import GeocodingCache, NominatimGeocoder
from config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

db.init_db()
conn = db.get_connection()

# Find voters who participated in 2026 elections but have no geocoded coords
rows = conn.execute("""
    SELECT DISTINCT v.vuid, v.address, v.city, v.zip
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-23'
      AND (v.geocoded = 0 OR v.geocoded IS NULL OR v.lat IS NULL)
      AND v.address IS NOT NULL AND v.address != ''
""").fetchall()

print(f"Found {len(rows)} ungeocoded 2026 voters with addresses")

if not rows:
    print("Nothing to geocode!")
    sys.exit(0)

# Initialize geocoder
cache = GeocodingCache(str(Config.GEOCODING_CACHE_FILE))
geocoder = NominatimGeocoder(cache)

success = 0
failed = 0

def geocode_one(row):
    vuid, address, city, zipcode = row
    full_addr = address
    if city:
        full_addr += f", {city}"
    if zipcode:
        full_addr += f", TX {zipcode}"
    else:
        full_addr += ", TX"
    
    result = geocoder.geocode(full_addr)
    return vuid, result, full_addr

print(f"Geocoding with 20 parallel workers...")
with ThreadPoolExecutor(max_workers=20) as executor:
    futures = {executor.submit(geocode_one, r): r for r in rows}
    for i, future in enumerate(as_completed(futures)):
        try:
            vuid, result, addr = future.result()
            if result and result.get('lat') is not None:
                conn.execute(
                    "UPDATE voters SET lat=?, lng=?, geocoded=1, updated_at=? WHERE vuid=?",
                    (result['lat'], result['lng'], datetime.now().isoformat(), vuid)
                )
                # Also cache it
                try:
                    db.cache_put(addr.strip().upper(), result['lat'], result['lng'],
                                 result.get('display_name', ''), 'aws')
                except Exception:
                    pass
                success += 1
            else:
                failed += 1
        except Exception as e:
            failed += 1
        
        if (i + 1) % 50 == 0:
            conn.commit()
            print(f"  Progress: {i+1}/{len(rows)} (geocoded: {success}, failed: {failed})")

conn.commit()
print(f"\nGeocoding complete: {success} geocoded, {failed} failed out of {len(rows)}")

# Now regenerate 2026 GeoJSON files
print("\nRegenerating 2026 GeoJSON files...")
import json

datasets_2026 = conn.execute("""
    SELECT DISTINCT v.county, ve.election_date, ve.party_voted, ve.voting_method
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-23'
      AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
""").fetchall()

data_dir = '/opt/whovoted/data'
public_data_dir = '/opt/whovoted/public/data'

for row in datasets_2026:
    county, election_date, party, voting_method = row
    print(f"  Regenerating: {county} {election_date} {party} {voting_method}")
    
    geojson = db.generate_geojson_for_election(
        county=county, election_date=election_date,
        party=party, voting_method=voting_method
    )
    
    features = geojson.get('features', [])
    geocoded_count = sum(1 for f in features if f.get('geometry') is not None)
    ungeocoded = len(features) - geocoded_count
    flipped = sum(1 for f in features if f.get('properties', {}).get('has_switched_parties'))
    new_voters = sum(1 for f in features if f.get('properties', {}).get('is_new_voter'))
    
    print(f"    {len(features)} voters, {geocoded_count} geocoded, {ungeocoded} ungeocoded, {flipped} flipped, {new_voters} new")
    
    year = election_date[:4]
    date_str = election_date.replace('-', '')
    party_lower = party.lower()
    party_suffix = '_democratic' if 'democrat' in party_lower else '_republican' if 'republican' in party_lower else f'_{party_lower}'
    method_suffix = '_ev' if 'early' in (voting_method or '').lower() else '_ed'
    
    map_filename = f'map_data_{county}_{year}_primary{party_suffix}_{date_str}{method_suffix}.json'
    meta_filename = f'metadata_{county}_{year}_primary{party_suffix}_{date_str}{method_suffix}.json'
    
    # Write to both data/ and public/data/
    for d in [data_dir, public_data_dir]:
        if os.path.exists(d):
            with open(os.path.join(d, map_filename), 'w') as f:
                json.dump(geojson, f)
    
    # Update metadata
    meta_path = os.path.join(data_dir, meta_filename)
    if os.path.exists(meta_path):
        with open(meta_path, 'r') as f:
            meta = json.load(f)
    else:
        meta = {'year': year, 'county': county, 'election_type': 'primary',
                'election_date': election_date, 'voting_method': voting_method,
                'primary_party': party_lower}
    
    meta['matched_vuids'] = geocoded_count
    meta['unmatched_vuids'] = ungeocoded
    meta['total_addresses'] = len(features)
    meta['successfully_geocoded'] = geocoded_count
    meta['new_voters'] = new_voters
    meta['flipped_voters'] = flipped
    meta['last_updated'] = datetime.now().isoformat()
    
    for d in [data_dir, public_data_dir]:
        if os.path.exists(d):
            with open(os.path.join(d, meta_filename), 'w') as f:
                json.dump(meta, f, indent=2)

print("\nDone!")
