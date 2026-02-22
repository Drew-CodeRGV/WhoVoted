#!/usr/bin/env python3
"""
Clear the geocoding cache to force re-geocoding with improved accuracy.
Run this script after updating the geocoding system.
"""

import json
from pathlib import Path

def clear_cache():
    """Clear the geocoding cache file."""
    script_dir = Path(__file__).parent
    project_dir = script_dir.parent
    cache_file = project_dir / 'data' / 'geocoding_cache.json'
    
    if cache_file.exists():
        # Backup the cache first
        backup_file = cache_file.with_suffix('.json.backup')
        import shutil
        shutil.copy2(cache_file, backup_file)
        print(f"✓ Backed up cache to: {backup_file}")
        
        # Clear the cache
        cache_file.unlink()
        print(f"✓ Cleared geocoding cache: {cache_file}")
        print("\nThe cache has been cleared. Next time you upload data,")
        print("all addresses will be re-geocoded with improved accuracy.")
        print("\nIf you need to restore the old cache, rename:")
        print(f"  {backup_file}")
        print("to:")
        print(f"  {cache_file}")
    else:
        print(f"Cache file not found: {cache_file}")
        print("Nothing to clear.")

if __name__ == '__main__':
    print("WhoVoted Geocoding Cache Clearer")
    print("=" * 50)
    print()
    
    response = input("Are you sure you want to clear the geocoding cache? (yes/no): ")
    
    if response.lower() in ['yes', 'y']:
        clear_cache()
    else:
        print("Cancelled. Cache was not cleared.")
