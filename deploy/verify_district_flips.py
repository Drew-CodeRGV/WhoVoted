#!/usr/bin/env python3
"""Verify district-stats flip numbers against direct DB queries."""
import sqlite3
import json

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row

# First, let's understand the data
print("=== Election dates in DB ===")
for r in conn.execute("SELECT DISTINCT election_date, COUNT(*) as cnt FROM voter_elections GROUP BY election_date ORDER BY election_date"):
    print(f"  {r['election_date']}: {r['cnt']} voters")

print("\n=== Flip definition check ===")
print("A flip for 2026 = voter whose party in 2026 differs from their party in the")
print("IMMEDIATELY PRECEDING election (the most recent election before 2026-03-03).")

# Get the immediately preceding election for each 2026 voter
print("\n=== What is the 'previous election' for 2026 voters? ===")
rows = conn.execute("""
    SELECT ve_prev.election_date, COUNT(*) as cnt
    FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    WHERE ve_current.election_date = '2026-03-03'
        AND ve_prev.election_date = (
            SELECT MAX(ve2.election_date) FROM voter_elections ve2
            WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    GROUP BY ve_prev.election_date
""").fetchall()
for r in rows:
    print(f"  Previous election: {r['election_date']} -> {r['cnt']} voters")

# Count total flips for 2026 (all voters, not just a district)
print("\n=== Total flips for 2026 (entire county) ===")
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
total_r2d = 0
total_d2r = 0
for r in rows:
    print(f"  {r['from_p']} -> {r['to_p']}: {r['cnt']}")
    if r['from_p'] == 'Republican' and r['to_p'] == 'Democratic':
        total_r2d += r['cnt']
    elif r['from_p'] == 'Democratic' and r['to_p'] == 'Republican':
        total_d2r += r['cnt']
print(f"\n  R->D: {total_r2d}")
print(f"  D->R: {total_d2r}")
print(f"  Total flips: {total_r2d + total_d2r}")

# Now let's spot-check: pick some specific flipped voters and verify
print("\n=== Spot-check: 5 R->D flippers ===")
flippers = conn.execute("""
    SELECT ve_current.vuid, ve_current.party_voted as now, ve_prev.party_voted as prev, ve_prev.election_date as prev_date
    FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    WHERE ve_current.election_date = '2026-03-03'
        AND ve_prev.election_date = (
            SELECT MAX(ve2.election_date) FROM voter_elections ve2
            WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
        AND ve_current.party_voted = 'Democratic'
        AND ve_prev.party_voted = 'Republican'
    LIMIT 5
""").fetchall()
for f in flippers:
    print(f"  VUID {f['vuid']}: {f['prev']} ({f['prev_date']}) -> {f['now']} (2026-03-03)")
    # Show full history
    history = conn.execute("SELECT election_date, party_voted FROM voter_elections WHERE vuid=? ORDER BY election_date", (f['vuid'],)).fetchall()
    for h in history:
        print(f"    {h['election_date']}: {h['party_voted']}")

print("\n=== Spot-check: 5 D->R flippers ===")
flippers = conn.execute("""
    SELECT ve_current.vuid, ve_current.party_voted as now, ve_prev.party_voted as prev, ve_prev.election_date as prev_date
    FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    WHERE ve_current.election_date = '2026-03-03'
        AND ve_prev.election_date = (
            SELECT MAX(ve2.election_date) FROM voter_elections ve2
            WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
        AND ve_current.party_voted = 'Republican'
        AND ve_prev.party_voted = 'Democratic'
    LIMIT 5
""").fetchall()
for f in flippers:
    print(f"  VUID {f['vuid']}: {f['prev']} ({f['prev_date']}) -> {f['now']} (2026-03-03)")
    history = conn.execute("SELECT election_date, party_voted FROM voter_elections WHERE vuid=? ORDER BY election_date", (f['vuid'],)).fetchall()
    for h in history:
        print(f"    {h['election_date']}: {h['party_voted']}")

conn.close()
