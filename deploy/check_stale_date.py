#!/usr/bin/env python3
"""Check the 2026-02-25 election records - likely stale from earlier upload."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# How many records for 2026-02-25?
rows = conn.execute("""
    SELECT party_voted, COUNT(*), MIN(source_file), MAX(source_file)
    FROM voter_elections
    WHERE election_date = '2026-02-25'
    GROUP BY party_voted
""").fetchall()

print("Records for 2026-02-25:")
for r in rows:
    print(f"  party={r[0]}, count={r[1]}, source_files: {r[2]} ... {r[3]}")

# Check if these are the same VUIDs as 2026-03-03
overlap = conn.execute("""
    SELECT COUNT(DISTINCT ve1.vuid)
    FROM voter_elections ve1
    JOIN voter_elections ve2 ON ve1.vuid = ve2.vuid
    WHERE ve1.election_date = '2026-02-25'
      AND ve2.election_date = '2026-03-03'
      AND ve2.party_voted = 'Democratic'
""").fetchone()
print(f"\nVUIDs in both 2026-02-25 and 2026-03-03 DEM: {overlap[0]}")

total_feb25 = conn.execute(
    "SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date='2026-02-25'"
).fetchone()
print(f"Total unique VUIDs in 2026-02-25: {total_feb25[0]}")
