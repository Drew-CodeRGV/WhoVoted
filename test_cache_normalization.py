"""Test cache normalization to debug cache misses."""
import sys
sys.path.insert(0, 'backend')

from geocoder import GeocodingCache
from config import Config

# Initialize cache
cache = GeocodingCache(str(Config.GEOCODING_CACHE_FILE))

# Test addresses from logs
test_addresses = [
    "6507 SOUTH GALAXY DRIVE, PHARR, TX 78577",
    "1602 LAKESHORE DRIVE, EDINBURG, TX 78541",
    "2804 NICKEL AVENUE, MISSION, TX 78574"
]

print(f"Cache has {cache.size()} entries\n")

# Get a few sample cache keys
import json
with open(Config.GEOCODING_CACHE_FILE, 'r') as f:
    cache_data = json.load(f)
    sample_keys = list(cache_data.keys())[:5]
    print("Sample cache keys:")
    for key in sample_keys:
        print(f"  {key}")

print("\n" + "="*80 + "\n")

# Test normalization
for addr in test_addresses:
    normalized = cache.normalize_address(addr)
    cached_result = cache.get(addr)
    
    print(f"Original:   {addr}")
    print(f"Normalized: {normalized}")
    print(f"In cache:   {'YES' if cached_result else 'NO'}")
    
    if not cached_result:
        # Try to find similar keys
        print("  Looking for similar keys in cache...")
        for key in list(cache_data.keys())[:100]:
            if "GALAXY" in key and "PHARR" in key:
                print(f"    Found similar: {key}")
            elif "LAKESHORE" in key and "EDINBURG" in key:
                print(f"    Found similar: {key}")
            elif "NICKEL" in key and "MISSION" in key:
                print(f"    Found similar: {key}")
    
    print()
