#!/usr/bin/env python3
"""Geocode voters who participated in 2026 elections but have no coordinates."""
import sys, os
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')

import database as db
from geocoder import GeocodingCache, NominatimGeocoder
from config import Config
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

db.init_db()
conn = db.get_connection()

# Find ALL ungeocoded voters who voted in any 2026 election
rows = conn.execute("""
    SELECT DISTINCT v.vuid, v.address, v.city, v.zip
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date LIKE '2026%'
      AND (v.geocoded = 0 OR v.geocoded IS NULL OR v.lat IS NULL)
      AND v.address IS NOT NULL AND v.address != ''
""").fetchall()

print(f"Found {len(rows)} ungeocoded 2026 voters with addresses")

if not rows:
    # Check if they have no address
    no_addr = conn.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date LIKE '2026%'
          AND (v.geocoded = 0 OR v.geocoded IS NULL OR v.lat IS NULL)
    """).fetchone()[0]
    
    no_addr_empty = conn.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date LIKE '2026%'
          AND (v.geocoded = 0 OR v.geocoded IS NULL OR v.lat IS NULL)
          AND (v.address IS NULL OR v.address = '')
    """).fetchone()[0]
    
    not_in_voters = conn.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        LEFT JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date LIKE '2026%' AND v.vuid IS NULL
    """).fetchone()[0]
    
    print(f"  Ungeocoded total: {no_addr}")
    print(f"  No address: {no_addr_empty}")
    print(f"  Not in voters table: {not_in_voters}")
    
    if no_addr_empty > 0 or not_in_voters > 0:
        print("\nThese voters need addresses from the voter registry to be geocoded.")
        print("They exist in voter_elections but either have no address or aren't in the voters table.")
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

# Regenerate the affected GeoJSON files
print("\nRegenerating 2026 GeoJSON files...")
import json

# Get all 2026 datasets
datasets = conn.execute("""
    SELECT DISTINCT v.county, ve.election_date, ve.party_voted, ve.voting_method
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date LIKE '2026%'
      AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
""").fetchall()

data_dir = '/opt/whovoted/data'
public_data_dir = '/opt/whovoted/public/data'

for row in datasets:
    county, election_date, party, voting_method = row
    print(f"  Regenerating: {county} {election_date} {party} {voting_method}")
    
    geojson = db.generate_geojson_for_election(
        county=county, election_date=election_date,
        party=party, voting_method=voting_method
    )
    
    features = geojson.get('features', [])
    geocoded_count = sum(1 for f in features if f.get('geometry') is not None)
    ungeocoded = len(features) - geocoded_count
    
    print(f"    {len(features)} voters, {geocoded_count} geocoded, {ungeocoded} still ungeocoded")
    
    year = election_date[:4]
    date_str = election_date.replace('-', '')
    party_lower = party.lower()
    party_suffix = '_democratic' if 'democrat' in party_lower else '_republican' if 'republican' in party_lower else f'_{party_lower}'
    method_suffix = '_ev' if 'early' in (voting_method or '').lower() else '_ed'
    
    map_filename = f'map_data_{county}_{year}_primary{party_suffix}_{date_str}{method_suffix}.json'
    meta_filename = f'metadata_{county}_{year}_primary{party_suffix}_{date_str}{method_suffix}.json'
    
    for d in [data_dir, public_data_dir]:
        if os.path.exists(d):
            with open(os.path.join(d, map_filename), 'w') as f:
                json.dump(geojson, f)
    
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
    meta['last_updated'] = datetime.now().isoformat()
    
    for d in [data_dir, public_data_dir]:
        if os.path.exists(d):
            with open(os.path.join(d, meta_filename), 'w') as f:
                json.dump(meta, f, indent=2)

print("\nDone!")
