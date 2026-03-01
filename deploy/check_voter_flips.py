#!/usr/bin/env python3
"""Check a specific voter's election history to verify flip detection."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

db.init_db()
conn = db.get_connection()

# Find SONJA ELISABETH WAASER
rows = conn.execute("""
    SELECT vuid, firstname, lastname, current_party, county
    FROM voters WHERE lastname LIKE '%WAASER%'
""").fetchall()

for r in rows:
    vuid = r[0]
    print(f"\n=== {r[1]} {r[2]} (VUID: {vuid}) ===")
    print(f"  Current party: {r[3]}")
    print(f"  County: {r[4]}")
    
    elections = conn.execute("""
        SELECT election_date, election_type, voting_method, party_voted
        FROM voter_elections WHERE vuid = ?
        ORDER BY election_date
    """, (vuid,)).fetchall()
    
    print(f"  Election history ({len(elections)} records):")
    for e in elections:
        print(f"    {e[0]} | {e[1]:10s} | {e[2]:15s} | {e[3]}")

# Also sample some "flipped" voters to see if they're real flips
print("\n\n=== Sample voters with 2+ elections and different parties ===")
flipped = conn.execute("""
    SELECT vuid, GROUP_CONCAT(party_voted || ' (' || election_date || ' ' || voting_method || ')', ' → ') as history
    FROM (
        SELECT DISTINCT vuid, party_voted, election_date, voting_method
        FROM voter_elections 
        WHERE party_voted != '' AND party_voted IS NOT NULL
        ORDER BY election_date
    )
    GROUP BY vuid
    HAVING COUNT(DISTINCT party_voted) >= 2
    LIMIT 10
""").fetchall()

for vuid, history in flipped:
    name = conn.execute("SELECT firstname, lastname FROM voters WHERE vuid = ?", (vuid,)).fetchone()
    name_str = f"{name[0]} {name[1]}" if name else "Unknown"
    print(f"  {vuid} ({name_str}): {history}")
