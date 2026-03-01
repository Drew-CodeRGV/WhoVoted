#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row

print("current_party for non-voted registered voters:")
for r in conn.execute("""
    SELECT v.current_party, COUNT(*) as cnt FROM voters v
    WHERE v.county='Hidalgo' AND v.vuid NOT IN (SELECT vuid FROM voter_elections WHERE election_date='2026-03-03')
    GROUP BY v.current_party ORDER BY cnt DESC LIMIT 10
"""):
    print(f"  '{r['current_party']}': {r['cnt']:,}")

conn.close()
