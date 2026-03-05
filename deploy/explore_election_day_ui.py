#!/usr/bin/env python3
"""
Explore the election day UI to find the actual API endpoints being used.

The UI at https://goelect.txelections.civixapps.com/ivis-evr-ui/evr
has a dropdown for elections and shows "Unofficial Election Day Turnout by County"
which suggests there's a working endpoint we haven't found yet.
"""

import json
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

CIVIX_BASE = 'https://goelect.txelections.civixapps.com'

# Try different endpoint patterns based on the UI structure
endpoints_to_try = [
    # County-level turnout (what the UI shows)
    '/api-ivis-system/api/v1/getElectionDayTurnout?electionId=53814',
    '/api-ivis-system/api/v1/getElectionDayTurnoutByCounty?electionId=53814',
    '/api-ivis-system/api/v1/getTurnout?type=ELECTION_DAY&electionId=53814',
    
    # File download patterns
    '/api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId=53814&electionDate=03/03/2026',
    '/api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId=53814&date=03/03/2026',
    '/api-ivis-system/api/v1/downloadFile?type=ELECTION_DAY&electionId=53814',
    
    # County-specific downloads
    '/api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId=53814&countyId=108',  # Hidalgo
    '/api-ivis-system/api/v1/getCountyFile?type=ELECTION_DAY&electionId=53814&countyId=108',
    
    # Alternative type names
    '/api-ivis-system/api/v1/getFile?type=ED_TURNOUT&electionId=53814',
    '/api-ivis-system/api/v1/getFile?type=ELECTION_DAY_ROSTER&electionId=53814',
    '/api-ivis-system/api/v1/getFile?type=OFFICIAL_ED&electionId=53814',
]

print("Testing election day API endpoints...")
print("=" * 80)

for endpoint in endpoints_to_try:
    url = CIVIX_BASE + endpoint
    print(f"\nTrying: {endpoint}")
    
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Referer': f'{CIVIX_BASE}/ivis-evr-ui/evr',
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
                print(f"  JSON keys: {list(parsed.keys())[:10]}")
                if isinstance(parsed, dict) and 'upload' in parsed:
                    print(f"  → Contains 'upload' field (base64 data)")
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
