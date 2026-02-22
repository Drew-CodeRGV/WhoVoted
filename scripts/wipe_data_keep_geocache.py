#!/usr/bin/env python3
"""
Script to wipe all uploaded voter data while preserving the geocoding cache.
This allows you to start fresh with uploads while keeping geocoded addresses.
"""

import json
import sys
from pathlib import Path
import shutil

def wipe_data(dry_run=False):
    """
    Wipe all uploaded data files while preserving geocoding cache.
    
    Args:
        dry_run: If True, only show what would be deleted without actually deleting
    """
    print("=" * 70)
    print("DATA WIPE UTILITY - Preserve Geocoding Cache")
    print("=" * 70)
    
    if dry_run:
        print("\n🔍 DRY RUN MODE - No files will be deleted\n")
    else:
        print("\n⚠️  WARNING: This will permanently delete all uploaded data!")
        print("Geocoding cache will be preserved.\n")
        
        response = input("Type 'DELETE' to confirm: ")
        if response != 'DELETE':
            print("Aborted.")
            return
        print()
    
    # Files to preserve
    preserve_files = [
        'geocoding_cache.json',
        'tx-county-outlines.json',
        'precinct_boundaries.json',
        'precinct_boundaries_cameron.json',
        'precinct_boundaries_combined.json'
    ]
    
    # Directories to clean
    directories = [
        Path('WhoVoted/data'),
        Path('WhoVoted/public/data'),
        Path('WhoVoted/uploads')
    ]
    
    deleted_count = 0
    preserved_count = 0
    
    for directory in directories:
        if not directory.exists():
            print(f"⚠️  Directory not found: {directory}")
            continue
        
        print(f"\n📁 Processing: {directory}")
        print("-" * 70)
        
        # Get all files in directory
        files = list(directory.glob('*'))
        
        for file_path in files:
            if file_path.is_file():
                filename = file_path.name
                
                # Check if file should be preserved
                if filename in preserve_files:
                    print(f"  ✓ PRESERVE: {filename}")
                    preserved_count += 1
                else:
                    if dry_run:
                        print(f"  🗑️  WOULD DELETE: {filename}")
                    else:
                        try:
                            file_path.unlink()
                            print(f"  ✗ DELETED: {filename}")
                            deleted_count += 1
                        except Exception as e:
                            print(f"  ❌ ERROR deleting {filename}: {e}")
    
    # Clean uploads directory completely (no files to preserve there)
    uploads_dir = Path('WhoVoted/uploads')
    if uploads_dir.exists():
        print(f"\n📁 Processing: {uploads_dir}")
        print("-" * 70)
        
        upload_files = list(uploads_dir.glob('*'))
        for file_path in upload_files:
            if file_path.is_file():
                if dry_run:
                    print(f"  🗑️  WOULD DELETE: {file_path.name}")
                else:
                    try:
                        file_path.unlink()
                        print(f"  ✗ DELETED: {file_path.name}")
                        deleted_count += 1
                    except Exception as e:
                        print(f"  ❌ ERROR deleting {file_path.name}: {e}")
    
    # Summary
    print("\n" + "=" * 70)
    if dry_run:
        print("DRY RUN SUMMARY:")
        print(f"  Would delete: {deleted_count} files")
        print(f"  Would preserve: {preserved_count} files")
        print("\nRun without --dry-run to actually delete files")
    else:
        print("WIPE COMPLETE:")
        print(f"  Deleted: {deleted_count} files")
        print(f"  Preserved: {preserved_count} files")
        print(f"\n✓ Geocoding cache preserved at: WhoVoted/data/geocoding_cache.json")
        
        # Show cache stats
        cache_file = Path('WhoVoted/data/geocoding_cache.json')
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    cache = json.load(f)
                print(f"  Cache contains {len(cache)} geocoded addresses")
            except:
                pass
    
    print("=" * 70)

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Wipe uploaded data while preserving geocoding cache'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    args = parser.parse_args()
    
    wipe_data(dry_run=args.dry_run)

if __name__ == '__main__':
    main()
