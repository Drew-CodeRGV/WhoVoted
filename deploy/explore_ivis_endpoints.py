#!/usr/bin/env python3
"""
Explore all IVIS system endpoints to find election day data.
"""

import json
import base64
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

CIVIX_BASE = 'https://goelect.txelections.civixapps.com'

# Try every possible type parameter
file_types = [
    'ELECTION_DAY',
    'ELECTION_DAY_STATEWIDE', 
    'ELECTION_DAY_ROSTER',
    'ELECTION_DAY_TURNOUT',
    'ED',
    'ED_ROSTER',
    'ED_TURNOUT',
    'OFFICIAL_ELECTION_DAY',
    'OFFICIAL_ED',
    'TURNOUT',
    'TURNOUT_ED',
    'TURNOUT_ELECTION_DAY',
    'ROSTER_ED',
    'ROSTER_ELECTION_DAY',
    'FINAL_ELECTION_DAY',
    'CERTIFIED_ELECTION_DAY',
]

election_id = '53814'  # 2026 Democratic Primary
election_date = '03/03/2026'

print("Testing all possible file type parameters...")
print("=" * 80)

for file_type in file_types:
    # Try with and without election date
    urls_to_try = [
        f'/api-ivis-system/api/v1/getFile?type={file_type}&electionId={election_id}',
        f'/api-ivis-system/api/v1/getFile?type={file_type}&electionId={election_id}&electionDate={election_date}',
    ]
    
    for endpoint in urls_to_try:
        url = CIVIX_BASE + endpoint
        print(f"\nTrying: type={file_type}")
        
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': f'{CIVIX_BASE}/ivis-evr-ui/evr',
        })
        
        try:
            with urlopen(req, timeout=5) as resp:
                data = resp.read()
                parsed = json.loads(data.decode('utf-8'))
                
                print(f"  ✓ SUCCESS! HTTP 200")
                print(f"  Response keys: {list(parsed.keys())}")
                
                if 'upload' in parsed:
                    # Try to decode and peek at content
                    try:
                        decoded = base64.b64decode(parsed['upload']).decode('utf-8', errors='replace')
                        lines = decoded.split('\n')[:3]
                        print(f"  Decoded content preview:")
                        for line in lines:
                            print(f"    {line[:100]}")
                    except:
                        print(f"  Upload field size: {len(parsed['upload'])} chars")
                
                break  # Found it!
                
        except HTTPError as e:
            if e.code != 500:  # Only show non-500 errors
                print(f"  HTTP {e.code}")
        except:
            pass

print("\n" + "=" * 80)
print("Search complete")
