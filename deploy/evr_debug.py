#!/usr/bin/env python3
"""Debug script to test EVR CSV download URL format."""
import json
import base64
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

CIVIX_BASE = 'https://goelect.txelections.civixapps.com'

# Fetch fresh election data
EVR_ELECTION_URL = f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_ELECTION'
req = Request(EVR_ELECTION_URL, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
raw = urlopen(req, timeout=30).read()
wrapper = json.loads(raw.decode('utf-8'))
decoded = base64.b64decode(wrapper['upload']).decode('utf-8')
data = json.loads(decoded)
print(f"Top keys: {list(data.keys())}")

elections = data.get('elections', [])
print(f"\n{len(elections)} elections found")

for e in elections[:3]:
    print(f"\nID: {e['id']}, Name: {e['election_name']}")
    dates = e.get('early_voting_dates', [])
    print(f"  {len(dates)} dates, first: {dates[0] if dates else 'none'}")

# Try different URL formats for the first election + first date
el = elections[0]
el_id = el['id']
date_id = el['early_voting_dates'][0]['date_turnout_id']
print(f"\nTesting downloads for election {el_id}, date_turnout_id {date_id}")

# Format 1: Original
urls = [
    f"{CIVIX_BASE}/api-ivis-system/api/v1/getFileByFormat?type=EVR_STATEWIDE&electionId={el_id}&electionDate={date_id}&county=ALL&countyId=0&format=csv",
    f"{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE&electionId={el_id}&electionDate={date_id}",
    f"{CIVIX_BASE}/api-ivis-system/api/v1/getFileByFormat?type=EVR_STATEWIDE&electionId={el_id}&dateTurnoutId={date_id}&county=ALL&countyId=0&format=csv",
    f"{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE&electionId={el_id}&dateTurnoutId={date_id}",
    f"{CIVIX_BASE}/api-ivis-system/api/v1/getFileByFormat?type=EVR_STATEWIDE&electionId={el_id}&electionDate={date_id}&format=csv",
]

for i, url in enumerate(urls):
    print(f"\n--- Format {i+1}: {url[:120]}...")
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': '*/*',
        'Referer': f'{CIVIX_BASE}/ivis-evr-ui/evr',
        'Origin': CIVIX_BASE,
    })
    try:
        with urlopen(req, timeout=30) as resp:
            content = resp.read()
            print(f"  ✅ Status: {resp.status}, Size: {len(content)} bytes")
            # Try to decode
            text = content.decode('utf-8', errors='replace')
            print(f"  First 200 chars: {text[:200]}")
            # Try base64
            try:
                decoded = base64.b64decode(content).decode('utf-8')
                print(f"  Base64 decoded first 200: {decoded[:200]}")
            except:
                pass
    except (URLError, HTTPError) as e:
        print(f"  ❌ Error: {e}")
