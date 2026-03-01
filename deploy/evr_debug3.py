#!/usr/bin/env python3
"""Debug: extract exact API call patterns from the Angular JS bundle."""
import re
from urllib.request import urlopen, Request

CIVIX_BASE = 'https://goelect.txelections.civixapps.com'

# Fetch the main JS bundle
req = Request(f'{CIVIX_BASE}/ivis-evr-ui/main.77b08a58f1f7c4e1.js', headers={'User-Agent': 'Mozilla/5.0'})
js = urlopen(req, timeout=30).read().decode('utf-8')

# Extract the getFileByFormat function and surrounding context
for m in re.finditer(r'getFileByFormat', js):
    start = max(0, m.start() - 20)
    end = min(len(js), m.end() + 300)
    print(f"\n=== getFileByFormat @{m.start()} ===")
    print(js[start:end])
    print()

# Extract generateStatewideReport
for m in re.finditer(r'generateStatewideReport', js):
    start = max(0, m.start() - 20)
    end = min(len(js), m.end() + 500)
    print(f"\n=== generateStatewideReport @{m.start()} ===")
    print(js[start:end])
    print()

# Extract getNewEarlyVotingTurnout
for m in re.finditer(r'getNewEarlyVotingTurnout', js):
    start = max(0, m.start() - 20)
    end = min(len(js), m.end() + 400)
    print(f"\n=== getNewEarlyVotingTurnout @{m.start()} ===")
    print(js[start:end])
    print()

# Extract getFile patterns with EVR
for m in re.finditer(r'getFile\?type=\$\{', js):
    start = max(0, m.start() - 30)
    end = min(len(js), m.end() + 200)
    print(f"\n=== getFile pattern @{m.start()} ===")
    print(js[start:end])
    print()
