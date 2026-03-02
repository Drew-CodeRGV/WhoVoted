#!/usr/bin/env python3
"""Test district lookup speed."""
import time
import requests

BASE_URL = 'http://localhost:5000'

def test_district(district_id, district_name):
    """Test district stats endpoint."""
    print(f"\nTesting {district_name} ({district_id})...")
    
    # Test with cache
    t0 = time.time()
    response = requests.get(f'{BASE_URL}/api/district_stats', params={
        'district_id': district_id,
        'district_name': district_name
    })
    elapsed = time.time() - t0
    
    if response.status_code == 200:
        data = response.json()
        total = data.get('total', 0)
        print(f"  ✓ Response time: {elapsed:.2f}s")
        print(f"  ✓ Total voters: {total:,}")
        print(f"  ✓ Has age_groups: {'age_groups' in data}")
        print(f"  ✓ Has county_breakdown: {'county_breakdown' in data}")
        if 'county_breakdown' in data:
            counties = list(data['county_breakdown'].keys())
            print(f"  ✓ Counties: {', '.join(counties)}")
    else:
        print(f"  ✗ Error: {response.status_code}")

if __name__ == '__main__':
    # Test TX-15 (multi-county district)
    test_district('TX-15', 'TX-15 Congressional District')
    
    # Test HD-37 (single county)
    test_district('HD-37', 'TX State House District 37')
    
    # Test TX-34 (multi-county district)
    test_district('TX-34', 'TX-34 Congressional District')
