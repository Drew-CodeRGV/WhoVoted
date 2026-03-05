#!/usr/bin/env python3
"""Check voting methods in database."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
rows = conn.execute("""
    SELECT voting_method, COUNT(*) as cnt
    FROM voter_elections
    WHERE election_date='2026-03-03'
    GROUP BY voting_method
""").fetchall()

print("Voting methods for 2026-03-03:")
for method, cnt in rows:
    print(f"  {method or '(null)'}: {cnt:,}")

total = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03'").fetchone()[0]
print(f"\nTotal: {total:,}")

conn.close()
