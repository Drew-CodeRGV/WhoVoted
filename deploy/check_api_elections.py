#!/usr/bin/env python3
"""Check /api/elections output."""
import urllib.request
import json

resp = urllib.request.urlopen('http://localhost:5000/api/elections')
data = json.loads(resp.read())

for e in data['elections']:
    print(f"{e['electionDate']} {e['votingMethod']:15s} {e['totalVoters']:>6,} voters, "
          f"parties={e['parties']}, counties={e['counties']}")
