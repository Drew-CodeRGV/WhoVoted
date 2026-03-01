#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=== Brooks County 2026 voter_elections ===")
rows = conn.execute("""
    SELECT party_voted, COUNT(DISTINCT vuid) as voters
    FROM voter_elections
    WHERE election_date='2026-03-03'
    AND vuid IN (
        SELECT DISTINCT vuid FROM voter_elections
        WHERE source_file LIKE '%Brooks%' OR source_file LIKE '%Voting_History%'
    )
    GROUP BY party_voted
""").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]} voters")

print("\n=== All Brooks source files ===")
rows = conn.execute("""
    SELECT source_file, party_voted, COUNT(DISTINCT vuid)
    FROM voter_elections
    WHERE source_file LIKE '%Voting_History%'
    GROUP BY source_file, party_voted
    ORDER BY source_file, party_voted
""").fetchall()
for r in rows:
    print(f"  {r[0][:60]}  {r[1]:12s}  {r[2]} voters")

print(f"\n=== Total unique Brooks VUIDs in 2026 primary ===")
row = conn.execute("""
    SELECT COUNT(DISTINCT vuid) FROM voter_elections
    WHERE source_file LIKE '%Voting_History%'
""").fetchone()
print(f"  {row[0]} unique voters")
