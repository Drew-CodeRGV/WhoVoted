#!/usr/bin/env python3
"""Test AWS Location Service geocoding."""

import sys
sys.path.insert(0, 'backend')

from geocoder import GeocodingCache, NominatimGeocoder
from config import Config

# Initialize geocoder
cache = GeocodingCache(str(Config.GEOCODING_CACHE_FILE))
geocoder = NominatimGeocoder(
    cache=cache,
    aws_place_index=Config.AWS_LOCATION_PLACE_INDEX if hasattr(Config, 'AWS_LOCATION_PLACE_INDEX') else None,
    aws_region=Config.AWS_DEFAULT_REGION if hasattr(Config, 'AWS_DEFAULT_REGION') else 'us-east-1'
)

# Test addresses
test_addresses = [
    "123 Main Street, McAllen, TX 78501",
    "1000 E Nolana Ave, McAllen, TX 78504",
    "2101 W Trenton Rd, Edinburg, TX 78539"
]

print("=" * 70)
print("AWS Location Service Geocoding Test")
print("=" * 70)

for address in test_addresses:
    print(f"\nTesting: {address}")
    print("-" * 70)
    
    result = geocoder.geocode(address)
    
    if result:
        print(f"✓ Success!")
        print(f"  Source: {result.get('source')}")
        print(f"  Latitude: {result['lat']}")
        print(f"  Longitude: {result['lng']}")
        print(f"  Display Name: {result['display_name']}")
        if result.get('source') == 'aws_location':
            print(f"  Relevance: {result.get('relevance', 'N/A')}")
    else:
        print(f"✗ Geocoding failed")

# Show stats
print("\n" + "=" * 70)
print("Geocoding Statistics")
print("=" * 70)
stats = geocoder.get_stats()
print(f"Total requests: {stats.get('total_requests', 0)}")
print(f"Cache hits: {stats.get('cache_hits', 0)}")
print(f"API calls: {stats.get('api_calls', 0)}")

if stats.get('aws_api_calls', 0) > 0:
    print(f"\n✓ AWS Location Service:")
    print(f"  API calls: {stats.get('aws_api_calls', 0)}")
    print(f"  Successes: {stats.get('aws_success', 0)}")
    print(f"  Failures: {stats.get('aws_failures', 0)}")
else:
    print(f"\n⚠ AWS Location Service: Not used")
    print(f"  Check that AWS credentials are configured")
    print(f"  Check that Place Index exists: {Config.AWS_LOCATION_PLACE_INDEX}")

if stats.get('census_api_calls', 0) > 0:
    print(f"\nCensus Bureau:")
    print(f"  API calls: {stats.get('census_api_calls', 0)}")
    print(f"  Successes: {stats.get('census_success', 0)}")

if stats.get('photon_api_calls', 0) > 0:
    print(f"\nPhoton:")
    print(f"  API calls: {stats.get('photon_api_calls', 0)}")
    print(f"  Successes: {stats.get('photon_success', 0)}")

print("\n" + "=" * 70)
