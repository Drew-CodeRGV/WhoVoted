#!/usr/bin/env python3
"""Check the order of elections returned by the API."""
import urllib.request
import json

url = "http://localhost:5000/api/elections"
data = json.loads(urllib.request.urlopen(url).read())

print("Elections order from /api/elections:")
for i, e in enumerate(data['elections']):
    print(f"  [{i}] {e['electionDate']} {e['votingMethod']:15s} {e['totalVoters']:>6d} voters")

print(f"\nDefault (index 0): {data['elections'][0]['votingMethod']} with {data['elections'][0]['totalVoters']} voters")
