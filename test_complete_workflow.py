#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Complete end-to-end workflow test"""

import requests
import time
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:5000"

def test_complete_workflow():
    """Test the complete WhoVoted workflow"""
    
    print("=" * 70)
    print("WhoVoted Complete Workflow Test")
    print("=" * 70)
    
    # Test 1: Public map loads
    print("\n[1/5] Testing public map access...")
    try:
        response = requests.get(BASE_URL)
        if response.status_code == 200:
            print("✓ Public map page loads successfully")
        else:
            print(f"✗ Public map failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Public map error: {e}")
        return False
    
    # Test 2: Map data accessible
    print("\n[2/5] Testing map data access...")
    try:
        response = requests.get(f"{BASE_URL}/data/map_data.json")
        if response.status_code == 200:
            data = response.json()
            feature_count = len(data.get('features', []))
            print(f"✓ Map data accessible ({feature_count} features)")
        else:
            print(f"✗ Map data failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Map data error: {e}")
        return False
    
    # Test 3: Admin login
    print("\n[3/5] Testing admin authentication...")
    try:
        session = requests.Session()
        response = session.post(
            f"{BASE_URL}/admin/login",
            json={"username": "admin", "password": "admin2026!"}
        )
        if response.status_code == 200 and response.json().get('success'):
            print("✓ Admin authentication successful")
        else:
            print(f"✗ Admin login failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Admin login error: {e}")
        return False
    
    # Test 4: Admin dashboard access
    print("\n[4/5] Testing admin dashboard access...")
    try:
        response = session.get(f"{BASE_URL}/admin")
        if response.status_code == 200 and "dashboard" in response.text.lower():
            print("✓ Admin dashboard accessible")
        else:
            print(f"✗ Admin dashboard failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Admin dashboard error: {e}")
        return False
    
    # Test 5: CSV upload and processing
    print("\n[5/5] Testing CSV upload and processing...")
    try:
        with open("sample_voter_data.csv", "rb") as f:
            files = {"file": ("sample_voter_data.csv", f, "text/csv")}
            response = session.post(f"{BASE_URL}/admin/upload", files=files)
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get('job_id')
            print(f"✓ CSV upload successful (Job ID: {job_id})")
            
            # Wait for processing to complete
            print("  Waiting for processing to complete...", end="", flush=True)
            max_wait = 60
            start_time = time.time()
            
            while time.time() - start_time < max_wait:
                status_response = session.get(f"{BASE_URL}/admin/status")
                if status_response.status_code == 200:
                    status = status_response.json()
                    if status.get("status") == "completed":
                        print(" Done!")
                        print(f"  ✓ Processed {status.get('processed_records')} records")
                        print(f"  ✓ Geocoded {status.get('geocoded_count')} addresses")
                        print(f"  ✓ Failed {status.get('failed_count')} addresses")
                        break
                    elif status.get("status") == "error":
                        print(f"\n  ✗ Processing failed: {status.get('error')}")
                        return False
                time.sleep(2)
            else:
                print("\n  ✗ Processing timeout")
                return False
        else:
            print(f"✗ CSV upload failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ CSV upload error: {e}")
        return False
    
    print("\n" + "=" * 70)
    print("✓ All tests passed! WhoVoted is fully functional.")
    print("=" * 70)
    print("\nAccess points:")
    print(f"  • Public Map: {BASE_URL}/")
    print(f"  • Admin Panel: {BASE_URL}/admin")
    print(f"  • Admin Credentials: admin / admin2026!")
    print("=" * 70)
    
    return True

if __name__ == "__main__":
    success = test_complete_workflow()
    sys.exit(0 if success else 1)
