#!/usr/bin/env python3
"""Check why 2026 EV datasets have unmatched voters."""
import json
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

db.init_db()
conn = db.get_connection()

data_dir = '/opt/whovoted/public/data'

for label, fname in [
    ('2026 DEM EV', 'map_data_Hidalgo_2026_primary_democratic_20260223_ev.json'),
    ('2026 REP EV', 'map_data_Hidalgo_2026_primary_republican_20260223_ev.json'),
]:
    with open(f'{data_dir}/{fname}', 'r') as f:
        geojson = json.load(f)
    
    features = geojson.get('features', [])
    total = 0
    matched = 0
    unmatched = 0
    no_coords = 0
    has_coords = 0
    sample_unmatched = []
    
    for feat in features:
        props = feat.get('properties', {})
        geom = feat.get('geometry')
        vuid = str(props.get('vuid', '')).strip()
        if vuid.endswith('.0'):
            vuid = vuid[:-2]
        if not vuid or not vuid.isdigit():
            continue
        total += 1
        
        coords = geom.get('coordinates', []) if geom else []
        if coords and len(coords) >= 2 and coords[0] != 0 and coords[1] != 0:
            has_coords += 1
        else:
            no_coords += 1
        
        row = conn.execute("SELECT vuid, geocoded FROM voters WHERE vuid = ?", (vuid,)).fetchone()
        if row:
            matched += 1
        else:
            unmatched += 1
            if len(sample_unmatched) < 5:
                sample_unmatched.append(vuid)
    
    print(f"\n=== {label} ({fname}) ===")
    print(f"Total VUIDs: {total:,}")
    print(f"In voter DB: {matched:,}")
    print(f"NOT in DB:   {unmatched:,}")
    print(f"Has coords in GeoJSON: {has_coords:,}")
    print(f"No coords in GeoJSON:  {no_coords:,}")
    if sample_unmatched:
        print(f"Sample unmatched VUIDs: {sample_unmatched}")
