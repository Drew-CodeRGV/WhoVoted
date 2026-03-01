#!/usr/bin/env python3
"""Backfill coordinates into map_data GeoJSON files from the voter DB.

For voters that have been geocoded in the DB but have no coordinates in the
GeoJSON files, this script updates the GeoJSON with the DB coordinates.
This is much faster than re-geocoding since the coords already exist.
"""
import json
import sys
from datetime import datetime

sys.path.insert(0, '/opt/whovoted/backend')
import database as db

db.init_db()
conn = db.get_connection()

data_dir = '/opt/whovoted/public/data'

# Process 2026 EV files that have unmatched (no-coord) voters
files = [
    'map_data_Hidalgo_2026_primary_democratic_20260223_ev.json',
    'map_data_Hidalgo_2026_primary_republican_20260223_ev.json',
]

for fname in files:
    filepath = f'{data_dir}/{fname}'
    print(f"\n=== Processing {fname} ===")
    
    with open(filepath, 'r') as f:
        geojson = json.load(f)
    
    features = geojson.get('features', [])
    updated = 0
    already_had = 0
    not_in_db = 0
    not_geocoded = 0
    
    for feat in features:
        props = feat.get('properties', {})
        geom = feat.get('geometry')
        
        # Check if already has valid coordinates
        coords = geom.get('coordinates', []) if geom else []
        if coords and len(coords) >= 2 and coords[0] != 0 and coords[1] != 0:
            already_had += 1
            continue
        
        # Get VUID
        vuid = str(props.get('vuid', '')).strip()
        if vuid.endswith('.0'):
            vuid = vuid[:-2]
        if not vuid or not vuid.isdigit():
            continue
        
        # Look up in voter DB
        row = conn.execute(
            "SELECT lat, lng FROM voters WHERE vuid = ? AND geocoded = 1",
            (vuid,)
        ).fetchone()
        
        if row and row[0] and row[1]:
            lat, lng = float(row[0]), float(row[1])
            # Update the GeoJSON feature
            if not geom:
                feat['geometry'] = {'type': 'Point', 'coordinates': [lng, lat]}
            else:
                feat['geometry']['coordinates'] = [lng, lat]
            props['geocoded'] = True
            updated += 1
        elif row:
            not_geocoded += 1
        else:
            not_in_db += 1
    
    print(f"  Already had coords: {already_had:,}")
    print(f"  Updated from DB:    {updated:,}")
    print(f"  Not geocoded in DB: {not_geocoded:,}")
    print(f"  Not in DB:          {not_in_db:,}")
    print(f"  Total features:     {len(features):,}")
    
    if updated > 0:
        # Write back
        with open(filepath, 'w') as f:
            json.dump(geojson, f)
        print(f"  ✅ Saved {fname} with {updated:,} new coordinates")
        
        # Update the metadata matched/unmatched counts
        meta_name = 'metadata_' + fname[len('map_data_'):]
        meta_path = f'{data_dir}/{meta_name}'
        try:
            with open(meta_path, 'r') as f:
                meta = json.load(f)
            
            # Recount matched (has coords) vs unmatched
            new_matched = already_had + updated
            new_unmatched = not_geocoded + not_in_db
            meta['total_geocoded'] = new_matched
            meta['total_failed'] = new_unmatched
            meta['geocode_rate'] = round(new_matched / len(features) * 100, 1) if features else 0
            meta['backfill_date'] = datetime.now().isoformat()
            
            with open(meta_path, 'w') as f:
                json.dump(meta, f, indent=2)
            print(f"  ✅ Updated {meta_name}")
        except Exception as e:
            print(f"  ⚠️ Could not update metadata: {e}")
    else:
        print(f"  No updates needed")

print("\nDone!")
