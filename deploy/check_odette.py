#!/usr/bin/env python3
"""Check Odette's data in the DB — is she in 2026 EV? Does she have coords?"""
import sqlite3

DB = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Find Odette at 600 Wichita
rows = conn.execute("""
    SELECT vuid, firstname, lastname, address, lat, lng, geocoded, precinct, current_party
    FROM voters
    WHERE firstname LIKE '%ODETTE%' AND address LIKE '%WICHITA%'
""").fetchall()

print("=== Voters matching ODETTE + WICHITA ===")
for r in rows:
    print(f"  VUID: {r['vuid']}")
    print(f"  Name: {r['firstname']} {r['lastname']}")
    print(f"  Address: {r['address']}")
    print(f"  Coords: ({r['lat']}, {r['lng']}) geocoded={r['geocoded']}")
    print(f"  Precinct: {r['precinct']}, Party: {r['current_party']}")
    
    # Check election participation
    elections = conn.execute("""
        SELECT election_date, party_voted, voting_method
        FROM voter_elections WHERE vuid = ?
        ORDER BY election_date
    """, (r['vuid'],)).fetchall()
    print(f"  Elections:")
    for e in elections:
        print(f"    {e['election_date']} | {e['party_voted']} | {e['voting_method']}")
    print()

# Also check how many voters at 600 Wichita
print("=== All voters at 600 WICHITA ===")
wichita = conn.execute("""
    SELECT vuid, firstname, lastname, address, lat, lng, geocoded
    FROM voters
    WHERE address LIKE '%600 WICHITA%'
    ORDER BY address
""").fetchall()
for r in wichita:
    print(f"  {r['vuid']} | {r['firstname']} {r['lastname']} | {r['address'][:60]} | geocoded={r['geocoded']} | ({r['lat']}, {r['lng']})")

# Check how many APT addresses exist in 2026 EV
print("\n=== Apartment addresses in 2026 EV ===")
apt_count = conn.execute("""
    SELECT COUNT(DISTINCT v.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND (v.address LIKE '%APT%' OR v.address LIKE '%APARTMENT%' OR v.address LIKE '%UNIT%' OR v.address LIKE '%STE%')
""").fetchone()[0]
total_2026 = conn.execute("""
    SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date = '2026-03-03'
""").fetchone()[0]
print(f"  Apartment voters: {apt_count:,} / {total_2026:,} total")

conn.close()
