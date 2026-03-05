#!/usr/bin/env python3
"""Test the live LLM endpoint with actual HTTP requests."""
import requests
import json
import sys

print("=" * 80)
print("TESTING LIVE LLM ENDPOINT")
print("=" * 80)

# Test queries
test_queries = [
    {
        "question": "Show me Female voters in TX-15 who voted in 2024 but not 2026",
        "context": {}
    },
    {
        "question": "Find voters who switched from Republican to Democratic",
        "context": {}
    },
    {
        "question": "Show me voters in Hidalgo County",
        "context": {"county": "Hidalgo"}
    }
]

base_url = "http://127.0.0.1:5000"

# First, check if we need authentication
print("\n[1/3] Checking LLM status endpoint...")
try:
    response = requests.get(f"{base_url}/api/llm/status")
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✓ LLM available: {data.get('available')}")
        print(f"  Models: {data.get('models', [])}")
    else:
        print(f"✗ Status check failed: {response.text}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n[2/3] Testing LLM query endpoint (without auth - should fail)...")
try:
    response = requests.post(
        f"{base_url}/api/llm/query",
        json=test_queries[0],
        headers={"Content-Type": "application/json"}
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 401:
        print("✓ Correctly requires authentication")
    else:
        print(f"Response: {response.text[:200]}")
except Exception as e:
    print(f"✗ Error: {e}")

print("\n[3/3] Note: Full authentication test requires valid session cookie")
print("The endpoint is working correctly if:")
print("  1. Status endpoint returns available=True")
print("  2. Query endpoint returns 401 Unauthorized without auth")
print("  3. Diagnosis script passed all tests")

print("\n" + "=" * 80)
print("ENDPOINT TEST COMPLETE")
print("=" * 80)
