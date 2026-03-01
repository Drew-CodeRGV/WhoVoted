#!/usr/bin/env python3
"""Quick test of /api/voters/at endpoint."""
import sqlite3, requests

db = sqlite3.connect('/opt/whovoted/data/whovoted.db')
db.row_factory = sqlite3.Row

# Get a real voter coordinate
row = db.execute("""
    SELECT v.lat, v.lng, v.address FROM voters v
    JOIN voter_elections ve ON ve.vuid = v.vuid
    WHERE v.county='Hidalgo' AND v.geocoded=1 AND v.lat IS NOT NULL
      AND ve.election_date='2026-03-03' AND ve.voting_method='early-voting'
    LIMIT 1
""").fetchone()

if not row:
    print("No test voter found")
    exit(1)

lat, lng, addr = row['lat'], row['lng'], row['address']
print(f"Test coords: {lat}, {lng}")
print(f"Test address: {addr}")

resp = requests.get('http://localhost:5000/api/voters/at', params={
    'lat': lat, 'lng': lng,
    'election_date': '2026-03-03',
    'voting_method': 'early-voting'
})
data = resp.json()
print(f"Response count: {data['count']}")
for v in data['voters'][:5]:
    print(f"  {v['name']} | {v['address']} | VUID:{v['vuid']} | {v['party_affiliation_current']}")
