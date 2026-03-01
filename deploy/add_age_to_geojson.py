#!/usr/bin/env python3
"""Backfill birth_year into all existing GeoJSON files from the voters DB."""
import json
import sqlite3
import glob
import os

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = '/opt/whovoted/public/data'

conn = sqlite3.connect(DB_PATH)

# Build VUID -> birth_year lookup
print("Building birth_year lookup from DB...")
rows = conn.execute("SELECT vuid, birth_year FROM voters WHERE birth_year IS NOT NULL AND birth_year > 0").fetchall()
birth_map = {r[0]: r[1] for r in rows}
print(f"  {len(birth_map):,} voters with birth_year")

# Process all GeoJSON files
geojson_files = glob.glob(os.path.join(DATA_DIR, 'map_data_*.json'))
print(f"\nFound {len(geojson_files)} GeoJSON files to process")

for filepath in sorted(geojson_files):
    filename = os.path.basename(filepath)
    with open(filepath, 'r') as f:
        data = json.load(f)
    
    features = data.get('features', [])
    updated = 0
    already = 0
    
    for feat in features:
        props = feat.get('properties', {})
        vuid = props.get('vuid', '')
        
        if 'birth_year' in props and props['birth_year']:
            already += 1
            continue
        
        if vuid in birth_map:
            props['birth_year'] = birth_map[vuid]
            updated += 1
        else:
            props['birth_year'] = 0
    
    with open(filepath, 'w') as f:
        json.dump(data, f)
    
    print(f"  {filename}: {updated} updated, {already} already had birth_year, {len(features)} total")

conn.close()
print("\nDone!")
