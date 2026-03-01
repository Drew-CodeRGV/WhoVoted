#!/usr/bin/env python3
"""Test the new DB-driven API endpoints."""
import requests
import json

BASE = 'https://politiquera.com'

# Test /api/elections
print("=== /api/elections ===")
r = requests.get(f'{BASE}/api/elections?county=Hidalgo')
data = r.json()
print(f"Status: {r.status_code}")
if data.get('success'):
    for e in data['elections']:
        print(f"  {e['electionDate']} | {e['votingMethod']:15s} | {e['totalVoters']:,} voters | parties: {e['parties']}")
else:
    print(f"  Error: {data}")

# Test /api/election-stats
print("\n=== /api/election-stats (2026-03-03) ===")
r = requests.get(f'{BASE}/api/election-stats?county=Hidalgo&election_date=2026-03-03')
data = r.json()
print(f"Status: {r.status_code}")
if data.get('success'):
    s = data['stats']
    print(f"  Total: {s['total']:,}")
    print(f"  DEM: {s['democratic']:,}, REP: {s['republican']:,}")
    print(f"  Geocoded: {s['geocoded']:,}")
    print(f"  Flipped R→D: {s['flipped_to_dem']:,}, D→R: {s['flipped_to_rep']:,}")
    print(f"  New voters: {s['new_voters']:,}")
else:
    print(f"  Error: {data}")

# Test /api/voters (small sample)
print("\n=== /api/voters (limit=3) ===")
r = requests.get(f'{BASE}/api/voters?county=Hidalgo&election_date=2026-03-03&limit=3')
data = r.json()
print(f"Status: {r.status_code}")
print(f"Features: {len(data.get('features', []))}")
for f in data.get('features', [])[:3]:
    p = f['properties']
    print(f"  {p['vuid']} | {p['name']:25s} | {p['party_affiliation_current']:12s} | flip={p['has_switched_parties']} | new={p['is_new_voter']}")
    geom = f.get('geometry')
    if geom:
        print(f"    coords: {geom['coordinates']}")

# Test /api/voters with bounds
print("\n=== /api/voters with bounds (McAllen area) ===")
r = requests.get(f'{BASE}/api/voters?county=Hidalgo&election_date=2026-03-03&sw_lat=26.1&sw_lng=-98.3&ne_lat=26.3&ne_lng=-98.1&limit=5')
data = r.json()
print(f"Status: {r.status_code}")
print(f"Features: {len(data.get('features', []))}")
for f in data.get('features', [])[:3]:
    p = f['properties']
    print(f"  {p['name']:25s} | {p['address'][:40]}")
