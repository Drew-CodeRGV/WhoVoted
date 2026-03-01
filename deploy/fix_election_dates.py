#!/usr/bin/env python3
"""Fix election dates: consolidate 2026-02-23 records into 2026-03-03 (the actual election date).

The first upload used the roster date (2026-02-23) as the election_date.
The second upload correctly used the election date (2026-03-03).
Both are for the same March 3, 2026 primary election.

This script:
1. Moves all 2026-02-23 voter_elections records to 2026-03-03
2. Handles conflicts (voter already has a 2026-03-03 record from the newer upload)
3. Regenerates all GeoJSON files
"""
import sys, os, json
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')
import database as db
from datetime import datetime
db.init_db()
conn = db.get_connection()

# Check current state
old_count = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = '2026-02-23'").fetchone()[0]
new_count = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = '2026-03-03'").fetchone()[0]
overlap = conn.execute("""
    SELECT COUNT(*) FROM voter_elections ve1
    JOIN voter_elections ve2 ON ve1.vuid = ve2.vuid AND ve1.voting_method = ve2.voting_method
    WHERE ve1.election_date = '2026-02-23' AND ve2.election_date = '2026-03-03'
""").fetchone()[0]

print(f"Current state:")
print(f"  2026-02-23 records: {old_count}")
print(f"  2026-03-03 records: {new_count}")
print(f"  Overlapping VUIDs (same voting_method): {overlap}")

# Strategy: 
# - For voters who have BOTH dates, keep the 2026-03-03 record (newer/cumulative) and delete the 2026-02-23 one
# - For voters who only have 2026-02-23, update to 2026-03-03

# Step 1: Delete 2026-02-23 records where voter already has a 2026-03-03 record
deleted = conn.execute("""
    DELETE FROM voter_elections 
    WHERE election_date = '2026-02-23' 
      AND EXISTS (
          SELECT 1 FROM voter_elections ve2 
          WHERE ve2.vuid = voter_elections.vuid 
            AND ve2.voting_method = voter_elections.voting_method
            AND ve2.election_date = '2026-03-03'
      )
""").rowcount
print(f"\nStep 1: Deleted {deleted} duplicate 2026-02-23 records (already have 2026-03-03)")

# Step 2: Update remaining 2026-02-23 records to 2026-03-03
remaining = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = '2026-02-23'").fetchone()[0]
print(f"Step 2: Updating {remaining} remaining 2026-02-23 records to 2026-03-03...")

updated = conn.execute("""
    UPDATE voter_elections 
    SET election_date = '2026-03-03', election_year = '2026'
    WHERE election_date = '2026-02-23'
""").rowcount
print(f"  Updated {updated} records")

conn.commit()

# Verify
final_old = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = '2026-02-23'").fetchone()[0]
final_new = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = '2026-03-03'").fetchone()[0]
print(f"\nAfter fix:")
print(f"  2026-02-23 records: {final_old}")
print(f"  2026-03-03 records: {final_new}")

# Check flip stats now
flips = conn.execute("""
    SELECT COUNT(*) FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    WHERE ve_current.election_date = '2026-03-03'
        AND ve_prev.election_date = (
            SELECT MAX(ve2.election_date) FROM voter_elections ve2
            WHERE ve2.vuid = ve_current.vuid
                AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
        )
        AND ve_current.party_voted != '' AND ve_current.party_voted IS NOT NULL
        AND ve_prev.party_voted != '' AND ve_prev.party_voted IS NOT NULL
        AND ve_current.party_voted != ve_prev.party_voted
""").fetchone()[0]
print(f"\nFlip count for 2026-03-03: {flips}")

# Regenerate ALL GeoJSON files
print("\nRegenerating ALL GeoJSON files...")
datasets = conn.execute("""
    SELECT DISTINCT v.county, ve.election_date, ve.party_voted, ve.voting_method
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.party_voted != '' AND ve.party_voted IS NOT NULL
    ORDER BY ve.election_date, ve.party_voted
""").fetchall()

data_dir = '/opt/whovoted/data'
public_data_dir = '/opt/whovoted/public/data'

for row in datasets:
    county, election_date, party, voting_method = row
    
    geojson = db.generate_geojson_for_election(
        county=county, election_date=election_date,
        party=party, voting_method=voting_method
    )
    
    features = geojson.get('features', [])
    geocoded = sum(1 for f in features if f.get('geometry') is not None)
    flipped = sum(1 for f in features if f.get('properties', {}).get('has_switched_parties'))
    new_voters = sum(1 for f in features if f.get('properties', {}).get('is_new_voter'))
    
    year = election_date[:4]
    date_str = election_date.replace('-', '')
    party_lower = party.lower()
    party_suffix = '_democratic' if 'democrat' in party_lower else '_republican' if 'republican' in party_lower else f'_{party_lower}'
    method_suffix = '_ev' if 'early' in (voting_method or '').lower() else '_ed'
    
    map_filename = f'map_data_{county}_{year}_primary{party_suffix}_{date_str}{method_suffix}.json'
    meta_filename = f'metadata_{county}_{year}_primary{party_suffix}_{date_str}{method_suffix}.json'
    
    print(f"  {map_filename}: {len(features)} voters, {geocoded} geocoded, {flipped} flipped, {new_voters} new")
    
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
    
    meta['matched_vuids'] = geocoded
    meta['unmatched_vuids'] = len(features) - geocoded
    meta['total_addresses'] = len(features)
    meta['successfully_geocoded'] = geocoded
    meta['flipped_voters'] = flipped
    meta['new_voters'] = new_voters
    meta['flip_logic'] = 'immediate_predecessor_only'
    meta['last_updated'] = datetime.now().isoformat()
    
    for d in [data_dir, public_data_dir]:
        if os.path.exists(d):
            with open(os.path.join(d, meta_filename), 'w') as f:
                json.dump(meta, f, indent=2)

# Also regenerate cumulative files for 2026
print("\nRegenerating 2026 cumulative files...")
for party in ['Democratic', 'Republican']:
    geojson = db.generate_geojson_for_election('Hidalgo', '2026-03-03', party, 'early-voting')
    features = geojson.get('features', [])
    flipped = sum(1 for f in features if f.get('properties', {}).get('has_switched_parties'))
    
    party_suffix = '_democratic' if 'democrat' in party.lower() else '_republican'
    cum_map = f'map_data_Hidalgo_2026_primary{party_suffix}_cumulative_ev.json'
    cum_meta = f'metadata_Hidalgo_2026_primary{party_suffix}_cumulative_ev.json'
    
    for d in [data_dir, public_data_dir]:
        if os.path.exists(d):
            with open(os.path.join(d, cum_map), 'w') as f:
                json.dump(geojson, f)
    
    # Update cumulative metadata
    for d in [data_dir, public_data_dir]:
        meta_path = os.path.join(d, cum_meta)
        if os.path.exists(meta_path):
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            meta['matched_vuids'] = len(features)
            meta['total_addresses'] = len(features)
            meta['successfully_geocoded'] = len(features)
            meta['flipped_voters'] = flipped
            meta['last_updated'] = datetime.now().isoformat()
            with open(meta_path, 'w') as f:
                json.dump(meta, f, indent=2)
    
    print(f"  {cum_map}: {len(features)} voters, {flipped} flipped")

# Clean up old 2026-02-23 files that no longer have data
print("\nCleaning up stale 2026-02-23 GeoJSON files...")
import glob
for pattern in ['map_data_*20260223*', 'metadata_*20260223*']:
    for f in glob.glob(os.path.join(public_data_dir, pattern)):
        os.remove(f)
        print(f"  Removed {os.path.basename(f)} from public/data")
    for f in glob.glob(os.path.join(data_dir, pattern)):
        os.remove(f)
        print(f"  Removed {os.path.basename(f)} from data")

# Also clean up the 20260224 day-snapshot files (they used the wrong roster date)
for pattern in ['map_data_*20260224*', 'metadata_*20260224*']:
    for f in glob.glob(os.path.join(public_data_dir, pattern)):
        os.remove(f)
        print(f"  Removed {os.path.basename(f)} from public/data")
    for f in glob.glob(os.path.join(data_dir, pattern)):
        os.remove(f)
        print(f"  Removed {os.path.basename(f)} from data")

print("\nDone!")
