#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row

print("registered_party distribution:")
for r in conn.execute("SELECT registered_party, COUNT(*) as cnt FROM voters WHERE county='Hidalgo' GROUP BY registered_party ORDER BY cnt DESC LIMIT 10"):
    print(f"  '{r['registered_party']}': {r['cnt']:,}")

print("\ncurrent_party distribution:")
for r in conn.execute("SELECT current_party, COUNT(*) as cnt FROM voters WHERE county='Hidalgo' GROUP BY current_party ORDER BY cnt DESC LIMIT 10"):
    print(f"  '{r['current_party']}': {r['cnt']:,}")

print("\nFor non-voted registered voters specifically:")
for r in conn.execute("""
    SELECT v.registered_party, COUNT(*) as cnt FROM voters v
    WHERE v.county='Hidalgo' AND v.vuid NOT IN (SELECT vuid FROM voter_elections WHERE election_date='2026-03-03')
    GROUP BY v.registered_party ORDER BY cnt DESC LIMIT 10
"""):
    print(f"  '{r['registered_party']}': {r['cnt']:,}")

conn.close()
