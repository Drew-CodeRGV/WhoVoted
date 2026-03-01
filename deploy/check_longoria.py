#!/usr/bin/env python3
"""Check DANIEL A LONGORIA's data in the DB and GeoJSON."""
import sys, os, json
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')
import database as db
db.init_db()
conn = db.get_connection()

# Find the voter
rows = conn.execute("""
    SELECT v.vuid, v.firstname, v.lastname, v.current_party,
           ve.election_date, ve.party_voted, ve.voting_method
    FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid
    WHERE v.lastname = 'LONGORIA' AND v.firstname LIKE 'DANIEL%'
    ORDER BY v.firstname, ve.election_date
""").fetchall()
print("=== DB election history ===")
for r in rows:
    print(f"  {r[1]} {r[2]} (VUID {r[0]}): {r[4]} {r[6]} -> {r[5]} (current_party: {r[3]})")

if rows:
    vuid = rows[0][0]
    # Check what's in the 2026 DEM GeoJSON
    print(f"\n=== In 2026 DEM EV GeoJSON (searching by VUID {vuid}) ===")
    with open('/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_democratic_20260223_ev.json') as f:
        gj = json.load(f)
    for feat in gj['features']:
        p = feat['properties']
        if p.get('vuid') == vuid:
            print(f"  vuid: {p['vuid']}")
            print(f"  has_switched_parties: {p['has_switched_parties']}")
            print(f"  party_affiliation_current: {p['party_affiliation_current']}")
            print(f"  party_affiliation_previous: {p['party_affiliation_previous']}")
            print(f"  is_new_voter: {p.get('is_new_voter')}")
            print(f"  party_history: {p.get('party_history')}")
            break
    else:
        print("  Not found by VUID, searching by name...")
        for feat in gj['features']:
            p = feat['properties']
            if 'LONGORIA' in (p.get('lastname','') or '') and 'DANIEL' in (p.get('firstname','') or ''):
                print(f"  vuid: {p['vuid']}, name: {p.get('firstname')} {p.get('lastname')}")
                print(f"  has_switched_parties: {p['has_switched_parties']}")
                print(f"  party_affiliation_current: {p['party_affiliation_current']}")
                print(f"  party_affiliation_previous: {p['party_affiliation_previous']}")
                print(f"  party_history: {p.get('party_history')}")
                break
