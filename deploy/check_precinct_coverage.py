#!/usr/bin/env python3
"""Check if zip-based filtering matches precinct-based filtering for McAllen ISD bond."""
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
ZIPS = ('78501','78502','78503','78504','78505')
ELECTION = '2026-05-10'
ph = ','.join('?' * len(ZIPS))

# Current approach: zip-based
zip_voters = conn.execute(f"""
    SELECT COUNT(DISTINCT ve.vuid) FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = ? AND v.zip IN ({ph})
""", (ELECTION,) + ZIPS).fetchone()[0]

# All bond voters
all_voters = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date = ?", (ELECTION,)).fetchone()[0]

# Voters in bond but NOT in McAllen zips
non_mcallen = conn.execute(f"""
    SELECT v.zip, v.city, COUNT(DISTINCT ve.vuid) as cnt
    FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = ? AND (v.zip NOT IN ({ph}) OR v.zip IS NULL)
    GROUP BY v.zip, v.city ORDER BY cnt DESC LIMIT 15
""", (ELECTION,) + ZIPS).fetchone()

print(f"All bond voters: {all_voters}")
print(f"McAllen zip voters: {zip_voters}")
print(f"Non-McAllen: {all_voters - zip_voters}")

# Show non-McAllen breakdown
rows = conn.execute(f"""
    SELECT v.zip, v.city, COUNT(DISTINCT ve.vuid) as cnt
    FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = ? AND (v.zip NOT IN ({ph}) OR v.zip IS NULL)
    GROUP BY v.zip, v.city ORDER BY cnt DESC LIMIT 20
""", (ELECTION,) + ZIPS).fetchall()
print("\nNon-McAllen voters by zip/city:")
for r in rows:
    print(f"  {r[0]} ({r[1]}): {r[2]}")

# Check precincts in roster vs McAllen
print("\nPrecincts of McAllen-zip bond voters:")
pct_rows = conn.execute(f"""
    SELECT v.precinct, COUNT(DISTINCT ve.vuid) as cnt
    FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = ? AND v.zip IN ({ph})
    GROUP BY v.precinct ORDER BY cnt DESC LIMIT 30
""", (ELECTION,) + ZIPS).fetchall()
for r in pct_rows:
    print(f"  Pct {r[0]}: {r[1]}")

conn.close()
