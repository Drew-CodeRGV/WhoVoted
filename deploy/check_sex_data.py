#!/usr/bin/env python3
"""Check sex/gender data in the voters table."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=== Sex field distribution in voters table ===")
rows = conn.execute("SELECT sex, COUNT(*) as cnt FROM voters GROUP BY sex ORDER BY cnt DESC").fetchall()
for r in rows:
    print(f"  '{r[0]}': {r[1]}")

total = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
with_sex = conn.execute("SELECT COUNT(*) FROM voters WHERE sex IS NOT NULL AND sex != ''").fetchone()[0]
print(f"\nTotal voters: {total}")
print(f"With sex data: {with_sex} ({round(with_sex/total*100,1)}%)")

# Check if 2026 voters have sex data
print("\n=== 2026 early voters with sex data ===")
rows = conn.execute("""
    SELECT v.sex, COUNT(*) as cnt 
    FROM voter_elections ve 
    JOIN voters v ON ve.vuid = v.vuid 
    WHERE ve.election_date = '2026-03-03'
    GROUP BY v.sex ORDER BY cnt DESC
""").fetchall()
for r in rows:
    print(f"  '{r[0]}': {r[1]}")

total_2026 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03'").fetchone()[0]
matched = sum(r[1] for r in rows if r[0] and r[0] != '')
print(f"\n2026 voters: {total_2026}")
print(f"Matched to voters table (have sex): {matched} ({round(matched/total_2026*100,1)}%)")

conn.close()
