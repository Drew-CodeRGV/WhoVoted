#!/usr/bin/env python3
"""Add sex field to existing GeoJSON files by looking up from voters table."""
import json
import sqlite3
import glob
import os

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = '/opt/whovoted/public/data'

conn = sqlite3.connect(DB_PATH)

# Build VUID -> sex lookup
print("Building VUID -> sex lookup...")
sex_map = {}
rows = conn.execute("SELECT vuid, sex FROM voters WHERE sex IS NOT NULL AND sex != ''").fetchall()
for r in rows:
    sex_map[r[0]] = r[1]
print(f"  {len(sex_map)} voters with sex data")

# Process all map_data files
files = sorted(glob.glob(os.path.join(DATA_DIR, 'map_data_*.json')))
print(f"\nProcessing {len(files)} GeoJSON files...")

for filepath in files:
    fname = os.path.basename(filepath)
    with open(filepath) as f:
        data = json.load(f)
    
    features = data.get('features', [])
    updated = 0
    for feat in features:
        props = feat.get('properties', {})
        vuid = props.get('vuid', '')
        if vuid and vuid in sex_map:
            props['sex'] = sex_map[vuid]
            updated += 1
        elif 'sex' not in props:
            props['sex'] = ''
    
    with open(filepath, 'w') as f:
        json.dump(data, f)
    
    print(f"  {fname}: {updated}/{len(features)} voters got sex data")

# Also update backend data dir
BACKEND_DIR = '/opt/whovoted/data'
backend_files = sorted(glob.glob(os.path.join(BACKEND_DIR, 'map_data_*.json')))
for filepath in backend_files:
    fname = os.path.basename(filepath)
    with open(filepath) as f:
        data = json.load(f)
    features = data.get('features', [])
    for feat in features:
        props = feat.get('properties', {})
        vuid = props.get('vuid', '')
        if vuid and vuid in sex_map:
            props['sex'] = sex_map[vuid]
        elif 'sex' not in props:
            props['sex'] = ''
    with open(filepath, 'w') as f:
        json.dump(data, f)

conn.close()
print("\nDone!")
