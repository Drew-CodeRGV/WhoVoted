#!/usr/bin/env python3
"""
Migrate existing data files to include voting method suffix (_ev or _ed).

This prevents filename collisions between early-voting and election-day data
for the same county/year/party/date.

Run on server: python3 /tmp/migrate_filenames.py
"""
import json
import os
import shutil
import glob

DATA_DIR = '/opt/whovoted/data'
PUBLIC_DIR = '/opt/whovoted/public/data'

def get_suffix(metadata):
    """Determine the correct suffix based on metadata."""
    vm = metadata.get('voting_method', '')
    is_early = metadata.get('is_early_voting', False)
    is_cum = metadata.get('is_cumulative', False)
    
    if is_early or is_cum or vm == 'early-voting':
        return '_ev'
    else:
        return '_ed'

def already_has_suffix(filename):
    """Check if filename already has _ev or _ed suffix before .json."""
    stem = filename.replace('.json', '')
    return stem.endswith('_ev') or stem.endswith('_ed')

def migrate_directory(directory):
    """Rename files in a directory to include voting method suffix."""
    if not os.path.exists(directory):
        print(f"Directory {directory} does not exist, skipping")
        return
    
    renamed = 0
    skipped = 0
    
    for meta_path in sorted(glob.glob(os.path.join(directory, 'metadata_*.json'))):
        basename = os.path.basename(meta_path)
        
        # Skip if already migrated
        if already_has_suffix(basename):
            print(f"  SKIP (already migrated): {basename}")
            skipped += 1
            continue
        
        # Skip default metadata.json
        if basename == 'metadata.json':
            continue
        
        try:
            with open(meta_path) as f:
                meta = json.load(f)
        except Exception as e:
            print(f"  ERROR reading {basename}: {e}")
            continue
        
        suffix = get_suffix(meta)
        
        # Rename metadata file
        new_meta_name = basename.replace('.json', f'{suffix}.json')
        new_meta_path = os.path.join(directory, new_meta_name)
        
        # Derive map_data filename
        map_data_name = basename.replace('metadata_', 'map_data_')
        map_data_path = os.path.join(directory, map_data_name)
        new_map_name = map_data_name.replace('.json', f'{suffix}.json')
        new_map_path = os.path.join(directory, new_map_name)
        
        print(f"  {basename} -> {new_meta_name}")
        os.rename(meta_path, new_meta_path)
        
        if os.path.exists(map_data_path):
            print(f"  {map_data_name} -> {new_map_name}")
            os.rename(map_data_path, new_map_path)
        else:
            print(f"  WARNING: {map_data_name} not found")
        
        renamed += 1
    
    print(f"  Renamed: {renamed}, Skipped: {skipped}")

print("=== Migrating /opt/whovoted/data/ ===")
migrate_directory(DATA_DIR)

print("\n=== Migrating /opt/whovoted/public/data/ ===")
migrate_directory(PUBLIC_DIR)

print("\nDone! Restart the app with: sudo supervisorctl restart whovoted")
