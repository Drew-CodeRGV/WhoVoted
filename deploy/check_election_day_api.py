#!/usr/bin/env python3
"""Check what election day endpoints are available."""

import json
import base64
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

CIVIX_BASE = 'https://goelect.txelections.civixapps.com'

# Get election data
print("Fetching election list...")
req = Request(f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_ELECTION', headers={
    'User-Agent': 'Mozilla/5.0',
    'Accept': 'application/json',
})

with urlopen(req, timeout=30) as resp:
    raw = resp.read()
    wrapper = json.loads(raw.decode('utf-8'))
    decoded = base64.b64decode(wrapper['upload']).decode('utf-8')
    data = json.loads(decoded)

# Find 2026 elections
for election in data['elections']:
    name = election.get('election_name', '')
    if '2026' in name and 'PRIMARY' in name.upper():
        print(f"\n{name}")
        print(f"  ID: {election.get('id')}")
        print(f"  Election Date: {election.get('election_date')}")
        
        # Check if election_day_dates exists
        if 'election_day_dates' in election:
            print(f"  Election Day Dates: {election['election_day_dates']}")
        
        # Try different API patterns
        election_id = election.get('id')
        patterns = [
            f'/api-ivis-system/api/v1/getFile?type=ELECTION_DAY_STATEWIDE&electionId={election_id}',
            f'/api-ivis-system/api/v1/getFile?type=OFFICIAL_ELECTION_DAY&electionId={election_id}',
            f'/api-ivis-system/api/v1/getFile?type=ED&electionId={election_id}',
            f'/api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId={election_id}',
        ]
        
        print(f"\n  Testing API endpoints:")
        for pattern in patterns:
            url = CIVIX_BASE + pattern
            try:
                req = Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
                with urlopen(req, timeout=10) as resp:
                    print(f"    ✓ {pattern}")
                    # Try to decode
                    try:
                        data = json.loads(resp.read().decode('utf-8'))
                        if 'upload' in data:
                            decoded = base64.b64decode(data['upload']).decode('utf-8')
                            print(f"      Data size: {len(decoded)} bytes")
                    except:
                        pass
            except HTTPError as e:
                print(f"    ✗ {pattern} - HTTP {e.code}")
            except Exception as e:
                print(f"    ✗ {pattern} - {type(e).__name__}")
