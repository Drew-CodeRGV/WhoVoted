"""Check if current AWS calls are actually in cache."""
import sys
import re
sys.path.insert(0, 'backend')

from geocoder import GeocodingCache
from config import Config

# Initialize cache
cache = GeocodingCache(str(Config.GEOCODING_CACHE_FILE))

# Sample addresses from recent AWS calls
test_addresses = [
    "7812 NORTH 27TH LANE, MCALLEN, TX 78504",
    "405 NEEDLE PALM, ALAMO, TX 78516",
    "2705 GARDENIA DRIVE, SAN JUAN, TX 78589",
    "1202 SOUTH BORDER AVENUE #508, WESLACO, TX 78596",
    "2301 NORTH ABRAM ROAD #531, MISSION, TX 78572"
]

print(f"Cache size: {cache.size()} entries\n")

for addr in test_addresses:
    normalized = cache.normalize_address(addr)
    cached_result = cache.get(addr)
    
    print(f"Address: {addr}")
    print(f"Normalized: {normalized}")
    print(f"In cache: {'YES' if cached_result else 'NO'}")
    
    if not cached_result:
        # Check if a similar address exists (without apartment number)
        base_addr = re.sub(r'\s+#\d+', '', addr)
        if base_addr != addr:
            base_normalized = cache.normalize_address(base_addr)
            base_cached = cache.get(base_addr)
            print(f"  Base address (no apt): {base_addr}")
            print(f"  Base in cache: {'YES' if base_cached else 'NO'}")
    
    print()
