#!/usr/bin/env python3
"""Quick check of /api/elections response."""
import json, urllib.request
resp = urllib.request.urlopen('http://localhost:5000/api/elections')
data = json.loads(resp.read())
elections = data.get('elections', [])
print(f"{len(elections)} elections found")
for e in elections[:8]:
    counties = e.get('counties', [])
    print(f"  {e['electionDate']} {e['votingMethod']}: {len(counties)} counties, {e['totalVoters']:,} voters")
    if len(counties) <= 10:
        print(f"    Counties: {', '.join(sorted(counties))}")
    else:
        print(f"    Counties: {', '.join(sorted(counties)[:5])}... +{len(counties)-5} more")
