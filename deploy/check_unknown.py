#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# Find VUIDs in voter_elections that have no voters row
rows = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid) 
    FROM voter_elections ve
    LEFT JOIN voters v ON ve.vuid = v.vuid
    WHERE v.vuid IS NULL
""").fetchone()
print(f"VUIDs in voter_elections with no voters row: {rows[0]}")

# Sample some
rows = conn.execute("""
    SELECT ve.vuid, ve.election_date, ve.party_voted, ve.source_file
    FROM voter_elections ve
    LEFT JOIN voters v ON ve.vuid = v.vuid
    WHERE v.vuid IS NULL
    LIMIT 10
""").fetchall()
for r in rows:
    print(f"  {r[0]}  {r[1]}  {r[2]}  {r[3][:50]}")
