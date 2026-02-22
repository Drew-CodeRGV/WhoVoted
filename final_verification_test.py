"""Final verification that cache will work before restart."""
import sys
import json
sys.path.insert(0, 'backend')

# Import the ACTUAL code that will run
from geocoder import GeocodingCache, NominatimGeocoder
from config import Config

print("="*80)
print("FINAL VERIFICATION TEST")
print("="*80)

# 1. Load cache exactly as Flask will
cache = GeocodingCache(str(Config.GEOCODING_CACHE_FILE))
print(f"\n1. Cache loaded: {cache.size()} entries")

# 2. Create geocoder exactly as Flask will
geocoder = NominatimGeocoder(cache)
print(f"2. Geocoder created with cache")

# 3. Test the EXACT addresses that will be geocoded
test_addresses = [
    "107 MILLER AVENUE, MISSION, TX 78572",
    "31 VILLAS JARDIN DRIVE, MCALLEN, TX 78503",
    "5501 NORTH 17TH STREET #14, MCALLEN, TX 78504",
    "1627 NORTH BRYAN ROAD, MISSION, TX 78572",
    "3006 SAN FEDERICO, MISSION, TX 78572"
]

print(f"\n3. Testing cache lookup with geocoder.geocode():")
print("-" * 80)

cache_hits = 0
api_calls = 0

for addr in test_addresses:
    # This is EXACTLY what the processor will call
    result = geocoder.geocode(addr)
    
    if result:
        # Check if it was from cache or API
        stats = geocoder.get_stats()
        current_cache_hits = stats['cache_hits']
        current_api_calls = stats['api_calls']
        
        was_cached = (current_cache_hits > cache_hits)
        cache_hits = current_cache_hits
        api_calls = current_api_calls
        
        print(f"✓ {addr[:50]}")
        print(f"  Source: {'CACHE' if was_cached else 'API CALL'}")
    else:
        print(f"✗ {addr[:50]} - FAILED")

print("\n" + "="*80)
print("FINAL STATS:")
print("="*80)
final_stats = geocoder.get_stats()
print(f"Total requests: {final_stats['total_requests']}")
print(f"Cache hits: {final_stats['cache_hits']}")
print(f"API calls: {final_stats['api_calls']}")
print(f"Cache hit rate: {final_stats['cache_hit_rate']:.1%}")

print("\n" + "="*80)
if final_stats['cache_hits'] == len(test_addresses):
    print("✓ SUCCESS: ALL addresses found in cache!")
    print("✓ Restarting Flask will use cached addresses")
    print("✓ NO AWS credits will be wasted")
else:
    print("✗ PROBLEM: Some addresses not in cache")
    print(f"✗ {final_stats['api_calls']} API calls were made")
    print("✗ DO NOT restart - there's still an issue")
print("="*80)
