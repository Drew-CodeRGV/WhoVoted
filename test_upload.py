#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script for CSV upload functionality"""

import requests
import time
import json
import sys

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

BASE_URL = "http://localhost:5000"

def test_upload_workflow():
    """Test the complete upload and processing workflow"""
    
    print("=" * 60)
    print("Testing WhoVoted CSV Upload Workflow")
    print("=" * 60)
    
    # Step 1: Login
    print("\n1. Testing login...")
    session = requests.Session()
    login_response = session.post(
        f"{BASE_URL}/admin/login",
        json={"username": "admin", "password": "admin2026!"}
    )
    
    if login_response.status_code == 200:
        print("✓ Login successful!")
        print(f"  Cookies: {session.cookies.get_dict()}")
    else:
        print(f"✗ Login failed: {login_response.status_code}")
        return
    
    # Step 2: Upload CSV
    print("\n2. Testing CSV upload...")
    with open("sample_voter_data.csv", "rb") as f:
        files = {"file": ("sample_voter_data.csv", f, "text/csv")}
        upload_response = session.post(
            f"{BASE_URL}/admin/upload",
            files=files
        )
    
    print(f"Upload response status: {upload_response.status_code}")
    print(f"Upload response text: {upload_response.text}")
    
    if upload_response.status_code == 200:
        try:
            result = upload_response.json()
            print(f"✓ Upload successful! Job ID: {result.get('job_id')}")
        except Exception as e:
            print(f"✗ Failed to parse JSON response: {e}")
            return
    else:
        print(f"✗ Upload failed: {upload_response.status_code}")
        print(f"Response: {upload_response.text}")
        return
    
    # Step 3: Monitor processing
    print("\n3. Monitoring processing status...")
    max_wait = 120  # 2 minutes max
    start_time = time.time()
    
    while time.time() - start_time < max_wait:
        status_response = session.get(f"{BASE_URL}/admin/status")
        
        if status_response.status_code == 200:
            status = status_response.json()
            
            if status.get("status") == "idle":
                print("✗ Processing ended unexpectedly (idle)")
                break
            
            if status.get("status") == "completed":
                print(f"\n✓ Processing completed!")
                print(f"  Total records: {status.get('total_records')}")
                print(f"  Processed: {status.get('processed_records')}")
                print(f"  Errors: {len(status.get('errors', []))}")
                
                # Show last few log messages
                logs = status.get("log_messages", [])
                if logs:
                    print("\n  Last log messages:")
                    for log in logs[-5:]:
                        print(f"    {log}")
                break
            
            if status.get("status") == "error":
                print(f"\n✗ Processing failed!")
                print(f"  Error: {status.get('error')}")
                break
            
            # Show progress
            progress = status.get("progress", 0)
            processed = status.get("processed_records", 0)
            total = status.get("total_records", 0)
            print(f"  Progress: {progress}% ({processed}/{total} records)", end="\r")
            
        time.sleep(2)
    else:
        print("\n✗ Processing timeout!")
    
    # Step 4: Check output files
    print("\n4. Checking output files...")
    try:
        map_data_response = requests.get(f"{BASE_URL}/data/map_data.json")
        if map_data_response.status_code == 200:
            map_data = map_data_response.json()
            print(f"✓ map_data.json exists with {len(map_data.get('features', []))} features")
        else:
            print(f"✗ map_data.json not accessible: {map_data_response.status_code}")
        
        metadata_response = requests.get(f"{BASE_URL}/data/metadata.json")
        if metadata_response.status_code == 200:
            metadata = metadata_response.json()
            print(f"✓ metadata.json exists")
            print(f"  Last updated: {metadata.get('last_updated')}")
            print(f"  Total addresses: {metadata.get('total_addresses')}")
            print(f"  Successfully geocoded: {metadata.get('successfully_geocoded')}")
        else:
            print(f"✗ metadata.json not accessible: {metadata_response.status_code}")
    except Exception as e:
        print(f"✗ Error checking output files: {e}")
    
    print("\n" + "=" * 60)
    print("Test complete!")
    print("=" * 60)

if __name__ == "__main__":
    test_upload_workflow()
