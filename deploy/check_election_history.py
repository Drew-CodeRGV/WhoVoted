#!/usr/bin/env python3
"""Check election history in the DB."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# What elections are in the DB?
rows = conn.execute("""
    SELECT election_date, party_voted, COUNT(*) as cnt
    FROM voter_elections
    WHERE party_voted != '' AND party_voted IS NOT NULL
    GROUP BY election_date, party_voted
    ORDER BY election_date, party_voted
""").fetchall()

print("Election history in DB:")
for r in rows:
    print(f"  {r[0]} | {r[1]}: {r[2]:,}")

# Total unique VUIDs with election history
total = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections").fetchone()
print(f"\nTotal unique VUIDs with election records: {total[0]:,}")

# Check if any 2024 voters switched to 2026 DEM
# (i.e., voted REP in 2024 and DEM in 2026)
cross = conn.execute("""
    SELECT COUNT(DISTINCT ve1.vuid) 
    FROM voter_elections ve1
    JOIN voter_elections ve2 ON ve1.vuid = ve2.vuid
    WHERE ve1.election_date = '2026-03-03' AND ve1.party_voted = 'Democratic'
      AND ve2.election_date = '2024-03-05' AND ve2.party_voted = 'Republican'
""").fetchone()
print(f"\nVoters who voted REP in 2024 and DEM in 2026: {cross[0]}")

cross2 = conn.execute("""
    SELECT COUNT(DISTINCT ve1.vuid) 
    FROM voter_elections ve1
    JOIN voter_elections ve2 ON ve1.vuid = ve2.vuid
    WHERE ve1.election_date = '2026-03-03' AND ve1.party_voted = 'Republican'
      AND ve2.election_date = '2024-03-05' AND ve2.party_voted = 'Democratic'
""").fetchone()
print(f"Voters who voted DEM in 2024 and REP in 2026: {cross2[0]}")
