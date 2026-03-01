#!/usr/bin/env python3
"""Backfill voters.geocoded flag from GeoJSON files.

For any voter that has coordinates in a GeoJSON file but geocoded=0 in the DB,
update the DB to reflect that they are geocoded.
"""
import json
import sqlite3
import glob
import os

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = '/opt/whovoted/public/data'

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA journal_mode=WAL")

# Find all map_data GeoJSON files
geojson_files = glob.glob(os.path.join(DATA_DIR, 'map_data_*.json'))
print(f"Found {len(geojson_files)} GeoJSON files")

total_updated = 0

for filepath in sorted(geojson_files):
    filename = os.path.basename(filepath)
    print(f"\nProcessing {filename}...")
    
    with open(filepath) as f:
        data = json.load(f)
    
    features = data.get('features', [])
    
    # Collect VUIDs that have valid coordinates
    vuids_with_coords = []
    for feat in features:
        props = feat.get('properties', {})
        coords = feat.get('geometry', {}).get('coordinates', [None, None])
        vuid = props.get('vuid', '')
        
        if vuid and coords and coords[0] is not None and coords[1] is not None:
            lat = coords[1]
            lng = coords[0]
            if lat != 0 and lng != 0:
                vuids_with_coords.append((lat, lng, vuid))
    
    print(f"  {len(vuids_with_coords):,} features with valid coords")
    
    # Update in batches
    updated = 0
    batch_size = 500
    for i in range(0, len(vuids_with_coords), batch_size):
        batch = vuids_with_coords[i:i+batch_size]
        for lat, lng, vuid in batch:
            cursor = conn.execute(
                "UPDATE voters SET lat=?, lng=?, geocoded=1 WHERE vuid=? AND (geocoded=0 OR geocoded IS NULL)",
                (lat, lng, vuid)
            )
            updated += cursor.rowcount
        conn.commit()
    
    print(f"  Updated {updated:,} voters")
    total_updated += updated

print(f"\n{'='*50}")
print(f"Total voters updated: {total_updated:,}")

# Show final stats
row = conn.execute("""
    SELECT COUNT(*),
           SUM(CASE WHEN geocoded=1 THEN 1 ELSE 0 END),
           SUM(CASE WHEN geocoded=0 OR geocoded IS NULL THEN 1 ELSE 0 END)
    FROM voters WHERE county='Hidalgo'
""").fetchone()
print(f"\nHidalgo County voters:")
print(f"  Total:        {row[0]:,}")
print(f"  Geocoded:     {row[1]:,}")
print(f"  Not geocoded: {row[2]:,}")
print(f"  Coverage:     {row[1]/row[0]*100:.1f}%")

conn.close()
