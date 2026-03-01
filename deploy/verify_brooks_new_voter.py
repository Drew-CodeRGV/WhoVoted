#!/usr/bin/env python3
"""Verify Brooks county voters are NOT marked as new voters."""
import json
import urllib.request

url = 'http://localhost:5000/api/voters?county=Brooks&election_date=2026-03-03&voting_method=early-voting'
resp = urllib.request.urlopen(url)
data = json.loads(resp.read())

feats = data.get('features', [])
new_count = sum(1 for f in feats if f['properties'].get('is_new_voter'))
print(f"Brooks: {len(feats)} voters, {new_count} marked as new (should be 0)")

# Also check stats
url2 = 'http://localhost:5000/api/election-stats?county=Brooks&election_date=2026-03-03&voting_method=early-voting'
resp2 = urllib.request.urlopen(url2)
stats = json.loads(resp2.read())
print(f"Stats new_voters: {stats.get('stats', {}).get('new_voters', 'N/A')} (should be 0)")

# Verify Hidalgo still has new voters
url3 = 'http://localhost:5000/api/election-stats?county=Hidalgo&election_date=2026-03-03&voting_method=early-voting'
resp3 = urllib.request.urlopen(url3)
stats3 = json.loads(resp3.read())
print(f"Hidalgo stats new_voters: {stats3.get('stats', {}).get('new_voters', 'N/A')} (should be > 0)")
