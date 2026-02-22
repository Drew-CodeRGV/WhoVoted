#!/usr/bin/env python3
"""
Script to fix existing map_data.json files by adding vuid field from cert field.
This ensures cross-referencing works for previously uploaded data.
"""

import json
import sys
from pathlib import Path

def fix_vuid_in_file(filepath):
    """Add vuid field from cert field if vuid is missing."""
    print(f"\nProcessing: {filepath}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if data.get('type') != 'FeatureCollection':
            print(f"  ⚠️  Not a FeatureCollection, skipping")
            return False
        
        features = data.get('features', [])
        if not features:
            print(f"  ⚠️  No features found, skipping")
            return False
        
        fixed_count = 0
        already_has_vuid = 0
        no_cert_available = 0
        
        for feature in features:
            props = feature.get('properties', {})
            
            # Check if vuid already exists
            if 'vuid' in props and props['vuid']:
                already_has_vuid += 1
                continue
            
            # Try to get cert field
            cert = props.get('cert')
            if cert and str(cert).strip() and str(cert).strip() != 'nan':
                props['vuid'] = str(cert)
                fixed_count += 1
            else:
                # Try ID field as fallback
                id_val = props.get('id')
                if id_val and str(id_val).isdigit() and len(str(id_val)) == 10:
                    props['vuid'] = str(id_val)
                    fixed_count += 1
                else:
                    no_cert_available += 1
        
        # Write back to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        
        print(f"  ✓ Fixed {fixed_count} records")
        print(f"  ℹ️  {already_has_vuid} records already had vuid")
        if no_cert_available > 0:
            print(f"  ⚠️  {no_cert_available} records have no cert or suitable ID")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def main():
    """Find and fix all map_data JSON files."""
    print("=" * 60)
    print("VUID Fixer - Adding vuid field from cert field")
    print("=" * 60)
    
    # Find all map_data files in public/data directory
    public_data_dir = Path('WhoVoted/public/data')
    
    if not public_data_dir.exists():
        print(f"Error: {public_data_dir} does not exist")
        sys.exit(1)
    
    # Find all map_data*.json files
    map_data_files = list(public_data_dir.glob('map_data*.json'))
    
    if not map_data_files:
        print("No map_data files found")
        sys.exit(0)
    
    print(f"\nFound {len(map_data_files)} map_data files to process\n")
    
    success_count = 0
    for filepath in sorted(map_data_files):
        if fix_vuid_in_file(filepath):
            success_count += 1
    
    print("\n" + "=" * 60)
    print(f"Completed: {success_count}/{len(map_data_files)} files processed successfully")
    print("=" * 60)

if __name__ == '__main__':
    main()
