#!/usr/bin/env python3
"""Test the voter history API fix."""
import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Find DANIEL LONGORIA
rows = conn.execute(
    "SELECT vuid, firstname, lastname FROM voters WHERE lastname LIKE 'LONGORIA' AND firstname LIKE 'DANIEL%' LIMIT 5"
).fetchall()

print("=== DANIEL LONGORIA voters ===")
for r in rows:
    print(f"  VUID: {r['vuid']}, Name: {r['firstname']} {r['lastname']}")
    # Get election history
    elections = conn.execute(
        "SELECT election_date, election_type, party_voted, voting_method FROM voter_elections WHERE vuid = ? ORDER BY election_date",
        (r['vuid'],)
    ).fetchall()
    for e in elections:
        print(f"    {e['election_date']} {e['election_type']} {e['voting_method']}: {e['party_voted']}")

# Also test a known flipped voter
print("\n=== Sample flipped voters ===")
flipped = conn.execute("""
    SELECT ve_current.vuid, ve_current.party_voted as cur, ve_prev.party_voted as prev,
           ve_current.election_date as cur_date, ve_prev.election_date as prev_date
    FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    WHERE ve_prev.election_date = (
        SELECT MAX(ve2.election_date) FROM voter_elections ve2
        WHERE ve2.vuid = ve_current.vuid
            AND ve2.election_date < ve_current.election_date
            AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
    )
    AND ve_current.party_voted != '' AND ve_current.party_voted IS NOT NULL
    AND ve_prev.party_voted != '' AND ve_prev.party_voted IS NOT NULL
    AND ve_current.party_voted != ve_prev.party_voted
    LIMIT 5
""").fetchall()

for f in flipped:
    print(f"  VUID: {f['vuid']}, {f['prev']} ({f['prev_date']}) -> {f['cur']} ({f['cur_date']})")
    # Get full history
    elections = conn.execute(
        "SELECT election_date, party_voted FROM voter_elections WHERE vuid = ? ORDER BY election_date",
        (f['vuid'],)
    ).fetchall()
    print(f"    Full history: {' -> '.join(e['party_voted'] + '(' + e['election_date'] + ')' for e in elections)}")

# Test the API endpoint
import urllib.request
for f in flipped[:2]:
    url = f"http://localhost:5000/api/voter-history/{f['vuid']}"
    try:
        resp = urllib.request.urlopen(url)
        data = json.loads(resp.read())
        print(f"\n  API response for {f['vuid']}:")
        for h in data.get('history', []):
            print(f"    {h['year']} {h['electionType']}: {h['party']}")
    except Exception as e:
        print(f"  API error for {f['vuid']}: {e}")

conn.close()
