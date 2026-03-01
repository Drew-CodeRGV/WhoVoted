#!/usr/bin/env python3
"""Fix 2026 metadata files to update matched_vuids/unmatched_vuids counts
based on actual coordinates in the GeoJSON files."""
import json

data_dir = '/opt/whovoted/public/data'

files = [
    ('map_data_Hidalgo_2026_primary_democratic_20260223_ev.json',
     'metadata_Hidalgo_2026_primary_democratic_20260223_ev.json'),
    ('map_data_Hidalgo_2026_primary_republican_20260223_ev.json',
     'metadata_Hidalgo_2026_primary_republican_20260223_ev.json'),
]

for map_file, meta_file in files:
    print(f"\n=== {meta_file} ===")
    
    # Count actual coords in GeoJSON
    with open(f'{data_dir}/{map_file}', 'r') as f:
        geojson = json.load(f)
    
    has_coords = 0
    no_coords = 0
    for feat in geojson.get('features', []):
        geom = feat.get('geometry')
        coords = geom.get('coordinates', []) if geom else []
        if coords and len(coords) >= 2 and coords[0] != 0 and coords[1] != 0:
            has_coords += 1
        else:
            no_coords += 1
    
    total = has_coords + no_coords
    print(f"  Has coords: {has_coords:,}")
    print(f"  No coords:  {no_coords:,}")
    print(f"  Total:       {total:,}")
    
    # Update metadata
    with open(f'{data_dir}/{meta_file}', 'r') as f:
        meta = json.load(f)
    
    old_matched = meta.get('matched_vuids', 0)
    old_unmatched = meta.get('unmatched_vuids', 0)
    
    meta['matched_vuids'] = has_coords
    meta['unmatched_vuids'] = no_coords
    meta['successfully_geocoded'] = has_coords
    meta['failed_addresses'] = no_coords
    
    with open(f'{data_dir}/{meta_file}', 'w') as f:
        json.dump(meta, f, indent=2)
    
    print(f"  Updated: matched {old_matched} -> {has_coords}, unmatched {old_unmatched} -> {no_coords}")

print("\nDone! Refresh the admin dashboard to see updated counts.")
