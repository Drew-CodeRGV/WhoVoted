#!/usr/bin/env python3
"""Test that address-based lookup catches all household members."""
import sqlite3, requests

db = sqlite3.connect('/opt/whovoted/data/whovoted.db')
db.row_factory = sqlite3.Row

# Find an address with multiple voters
row = db.execute("""
    SELECT v.address, v.lat, v.lng, COUNT(*) as cnt
    FROM voters v
    JOIN voter_elections ve ON ve.vuid = v.vuid
    WHERE v.county='Hidalgo' AND v.geocoded=1 AND v.lat IS NOT NULL
      AND ve.election_date='2026-03-03' AND ve.voting_method='early-voting'
    GROUP BY v.address
    HAVING cnt >= 3
    LIMIT 1
""").fetchone()

if not row:
    print("No multi-voter address found")
    exit(1)

print(f"Address: {row['address']}")
print(f"DB count at this address: {row['cnt']}")
print(f"Coords: {row['lat']}, {row['lng']}")

resp = requests.get('http://localhost:5000/api/voters/at', params={
    'lat': row['lat'], 'lng': row['lng'],
    'election_date': '2026-03-03',
    'voting_method': 'early-voting'
})
data = resp.json()
print(f"API returned: {data['count']} voters")
for v in data['voters']:
    print(f"  {v['name']} | {v['address']} | VUID:{v['vuid']} | {v['party_affiliation_current']}")
    if v['is_new_voter']:
        print(f"    ⭐ New voter")
    if v['has_switched_parties']:
        print(f"    ↩ Flipped from {v['party_affiliation_previous']}")
