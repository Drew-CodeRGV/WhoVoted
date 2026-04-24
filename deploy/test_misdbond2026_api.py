#!/usr/bin/env python3
"""Test McAllen ISD Bond 2026 API endpoints."""

import requests
import json

BASE_URL = 'https://politiquera.com'

def test_stats():
    """Test stats endpoint."""
    print("Testing /api/misdbond2026/stats...")
    try:
        response = requests.get(f'{BASE_URL}/api/misdbond2026/stats', timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total voters: {data.get('total_voters', 'N/A')}")
            print(f"Precincts: {data.get('precincts_count', 'N/A')}")
            print("✓ Stats endpoint working")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")

def test_voters():
    """Test voters endpoint."""
    print("\nTesting /api/misdbond2026/voters...")
    try:
        response = requests.get(f'{BASE_URL}/api/misdbond2026/voters', timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Voter count: {data.get('count', 'N/A')}")
            if data.get('voters'):
                print(f"First voter: {data['voters'][0].get('name', 'N/A')}")
            print("✓ Voters endpoint working")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")

def test_cache():
    """Test cache file."""
    print("\nTesting /cache/misdbond2026_voters.json...")
    try:
        response = requests.get(f'{BASE_URL}/cache/misdbond2026_voters.json', timeout=10)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Cached voter count: {data.get('count', 'N/A')}")
            print("✓ Cache file working")
        else:
            print(f"✗ Error: {response.text}")
    except Exception as e:
        print(f"✗ Exception: {e}")

if __name__ == '__main__':
    test_stats()
    test_voters()
    test_cache()
    print("\n✓ All tests complete")
