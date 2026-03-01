#!/usr/bin/env python3
"""Verify the flip logic fix by checking specific voters."""
import sys, os, json
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')

import database as db
db.init_db()
conn = db.get_connection()

# Check SONJA WAASER's history
print("=== SONJA WAASER election history ===")
rows = conn.execute("""
    SELECT v.firstname, v.lastname, ve.election_date, ve.party_voted
    FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid
    WHERE v.lastname = 'WAASER' AND v.firstname LIKE 'SONJA%'
    ORDER BY ve.election_date
""").fetchall()
for r in rows:
    print(f"  {r[0]} {r[1]}: {r[2]} -> {r[3]}")

# Check her flip status in the 2026 GeoJSON
print("\n=== In 2026 REP GeoJSON ===")
with open('/opt/whovoted/data/map_data_Hidalgo_2026_primary_republican_20260223_ev.json') as f:
    gj = json.load(f)
for feat in gj['features']:
    p = feat['properties']
    if 'WAASER' in (p.get('lastname', '') or '').upper():
        print(f"  {p.get('firstname')} {p.get('lastname')}")
        print(f"  has_switched_parties: {p.get('has_switched_parties')}")
        print(f"  party_current: {p.get('party_affiliation_current')}")
        print(f"  party_previous: {p.get('party_affiliation_previous')}")

# Overall flip stats
print("\n=== 2026 flip counts ===")
for party in ['Democratic', 'Republican']:
    fname = f'map_data_Hidalgo_2026_primary_{party.lower()}_20260223_ev.json'
    fpath = os.path.join('/opt/whovoted/data', fname)
    if os.path.exists(fpath):
        with open(fpath) as f:
            gj = json.load(f)
        total = len(gj['features'])
        flipped = sum(1 for feat in gj['features'] if feat['properties'].get('has_switched_parties'))
        print(f"  {party}: {total} voters, {flipped} flipped")

# Per-election flip counts from DB
print("\n=== Per-election flip counts from DB ===")
summary = db.get_election_summary()
for date, count in summary.get('per_election_flips', {}).items():
    print(f"  {date}: {count} flips")
