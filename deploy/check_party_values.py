#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cur = conn.cursor()

print("Distinct party_voted values:")
cur.execute("SELECT DISTINCT party_voted, COUNT(*) FROM voter_elections WHERE election_date = '2026-03-03' GROUP BY party_voted")
for row in cur.fetchall():
    print(f"  '{row[0]}': {row[1]:,}")

print("\nDistinct voting_method values:")
cur.execute("SELECT DISTINCT voting_method, COUNT(*) FROM voter_elections WHERE election_date = '2026-03-03' GROUP BY voting_method")
for row in cur.fetchall():
    print(f"  '{row[0]}': {row[1]:,}")

print("\nSample records:")
cur.execute("SELECT vuid, party_voted, voting_method FROM voter_elections WHERE election_date = '2026-03-03' LIMIT 10")
for row in cur.fetchall():
    print(f"  {row}")

conn.close()
