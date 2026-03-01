#!/usr/bin/env python3
"""Check the live API response."""
import urllib.request
import json

resp = urllib.request.urlopen('http://localhost:5000/admin/election-datasets')
data = json.loads(resp.read())

print(f"{'date':12s} {'county':8s} {'method':15s} {'party':12s} {'total':>6s} {'geo':>6s} {'ungeo':>6s} {'rate':>6s}")
print("-" * 90)
for d in data:
    total = d.get('total_voters', 0)
    geo = d.get('geocoded_count', 0)
    ungeo = d.get('ungeocoded_count', 0)
    rate = (geo / total * 100) if total > 0 else 0
    print(f"{d['election_date']:12s} {d.get('county','?'):8s} {d['voting_method']:15s} {d['party_voted']:12s} "
          f"{total:>6,} {geo:>6,} {ungeo:>6,} {rate:>5.1f}%")
