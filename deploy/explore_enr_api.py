#!/usr/bin/env python3
"""
Explore the Election Night Results (ENR) API to find voter turnout data.

The ENR system at https://goelect.txelections.civixapps.com/ivis-enr-ui/races
shows election results and may have turnout data we can extract.
"""

import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

CIVIX_BASE = 'https://goelect.txelections.civixapps.com'

# Common ENR API patterns
endpoints_to_try = [
    # Election list
    '/api-ivis-system/api/v1/getElections',
    '/api-ivis-system/api/v1/getElectionList',
    '/api-enr-system/api/v1/getElections',
    
    # Turnout data
    '/api-enr-system/api/v1/getTurnout?electionId=53814',
    '/api-enr-system/api/v1/getVoterTurnout?electionId=53814',
    '/api-enr-system/api/v1/getElectionData?electionId=53814',
    
    # Results data (may include turnout)
    '/api-enr-system/api/v1/getResults?electionId=53814',
    '/api-enr-system/api/v1/getRaces?electionId=53814',
    '/api-enr-system/api/v1/getElectionResults?electionId=53814',
    
    # County-level data
    '/api-enr-system/api/v1/getCountyResults?electionId=53814',
    '/api-enr-system/api/v1/getCountyTurnout?electionId=53814',
    
    # Summary/stats
    '/api-enr-system/api/v1/getSummary?electionId=53814',
    '/api-enr-system/api/v1/getStats?electionId=53814',
    '/api-enr-system/api/v1/getElectionSummary?electionId=53814',
    
    # File downloads
    '/api-enr-system/api/v1/getFile?type=TURNOUT&electionId=53814',
    '/api-enr-system/api/v1/getFile?type=RESULTS&electionId=53814',
    '/api-enr-system/api/v1/downloadTurnout?electionId=53814',
]

print("Exploring Election Night Results (ENR) API...")
print("=" * 80)

for endpoint in endpoints_to_try:
    url = CIVIX_BASE + endpoint
    print(f"\nTrying: {endpoint}")
    
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': f'{CIVIX_BASE}/ivis-enr-ui/races',
    })
    
    try:
        with urlopen(req, timeout=10) as resp:
            status = resp.status
            content_type = resp.headers.get('Content-Type', '')
            data = resp.read()
            
            print(f"  ✓ HTTP {status} - {content_type}")
            print(f"  Response size: {len(data)} bytes")
            
            # Try to parse as JSON
            try:
                parsed = json.loads(data.decode('utf-8'))
                
                # Show structure
                if isinstance(parsed, dict):
                    keys = list(parsed.keys())
                    print(f"  JSON keys: {keys[:10]}")
                    
                    # Look for interesting fields
                    if 'turnout' in str(parsed).lower():
                        print(f"  → Contains 'turnout' data!")
                    if 'voters' in str(parsed).lower():
                        print(f"  → Contains 'voters' data!")
                    if 'upload' in parsed:
                        print(f"  → Contains 'upload' field (base64 data)")
                    
                    # Show sample of data
                    for key in ['turnout', 'voters', 'results', 'data', 'elections']:
                        if key in parsed:
                            val = parsed[key]
                            if isinstance(val, list) and len(val) > 0:
                                print(f"  {key}: {len(val)} items")
                                print(f"    Sample: {str(val[0])[:100]}")
                            elif isinstance(val, dict):
                                print(f"  {key}: {list(val.keys())[:5]}")
                
                elif isinstance(parsed, list):
                    print(f"  JSON array: {len(parsed)} items")
                    if len(parsed) > 0:
                        print(f"    Sample: {str(parsed[0])[:100]}")
                
            except:
                # Not JSON, show first 200 chars
                preview = data.decode('utf-8', errors='replace')[:200]
                print(f"  Preview: {preview}")
            
    except HTTPError as e:
        print(f"  ✗ HTTP {e.code} - {e.reason}")
    except URLError as e:
        print(f"  ✗ Connection error: {e.reason}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

print("\n" + "=" * 80)
print("Exploration complete")
print("\nNote: ENR (Election Night Results) systems typically show:")
print("  - Vote counts by race/candidate")
print("  - Turnout statistics by county/precinct")
print("  - May not have individual voter records (that's EVR data)")
