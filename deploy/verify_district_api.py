#!/usr/bin/env python3
"""Verify district-stats API returns correct flip numbers by comparing
API results against direct DB queries for the same set of VUIDs."""
import sqlite3
import requests
import json

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# Get ALL 2026 VUIDs to test with the full county
all_vuids = [r[0] for r in conn.execute(
    "SELECT DISTINCT vuid FROM voter_elections WHERE election_date='2026-03-03'"
).fetchall()]
print(f"Total 2026 VUIDs: {len(all_vuids)}")

# Direct DB query for flips
rows = conn.execute("""
    SELECT ve_current.party_voted as to_p, ve_prev.party_voted as from_p, COUNT(*) as cnt
    FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    WHERE ve_current.election_date = '2026-03-03'
        AND ve_prev.election_date = (
            SELECT MAX(ve2.election_date) FROM voter_elections ve2
            WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
        AND ve_current.party_voted != ve_prev.party_voted
        AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
    GROUP BY ve_current.party_voted, ve_prev.party_voted
""").fetchall()
db_r2d = sum(r[2] for r in rows if r[1] == 'Republican' and r[0] == 'Democratic')
db_d2r = sum(r[2] for r in rows if r[1] == 'Democratic' and r[0] == 'Republican')
print(f"\nDirect DB: R->D={db_r2d}, D->R={db_d2r}")

# API query with ALL VUIDs
resp = requests.post('http://localhost:5000/api/district-stats',
    json={'vuids': all_vuids, 'district_id': 'ALL', 'election_date': '2026-03-03'},
    timeout=120)
data = resp.json()
print(f"API result: R->D={data['r2d']}, D->R={data['d2r']}")
print(f"API total={data['total']}, dem={data['dem']}, rep={data['rep']}, dem_share={data['dem_share']}")
print(f"API new_total={data['new_total']}, new_dem={data['new_dem']}, new_rep={data['new_rep']}")
print(f"API total_2024={data['total_2024']}, dem_2024={data['dem_2024']}, rep_2024={data['rep_2024']}")

# Compare
if data['r2d'] == db_r2d and data['d2r'] == db_d2r:
    print("\n✅ FLIP NUMBERS MATCH PERFECTLY")
else:
    print(f"\n❌ MISMATCH! DB: R->D={db_r2d}, D->R={db_d2r} vs API: R->D={data['r2d']}, D->R={data['d2r']}")

# Also verify total, dem, rep
db_total = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03'").fetchone()[0]
db_dem = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Democratic'").fetchone()[0]
db_rep = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Republican'").fetchone()[0]
print(f"\nDB total={db_total}, dem={db_dem}, rep={db_rep}")
if data['total'] == db_total and data['dem'] == db_dem and data['rep'] == db_rep:
    print("✅ TOTALS MATCH")
else:
    print(f"❌ TOTALS MISMATCH")

conn.close()
