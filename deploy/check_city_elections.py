#!/usr/bin/env python3
"""Check what election dates we have that might include city commission races."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)

# All election dates
print("All election dates in DB:")
dates = conn.execute("""
    SELECT election_date, COUNT(DISTINCT vuid) as voters, election_type
    FROM voter_elections
    GROUP BY election_date
    ORDER BY election_date DESC
""").fetchall()
for d, cnt, etype in dates:
    print(f"  {d}: {cnt:,} voters ({etype or '?'})")

# Check May 2026 specifically (bond + city elections were joint)
print("\nMay 2026 voters (bond election — may include city races):")
may = conn.execute("""
    SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date = '2026-05-10'
""").fetchone()[0]
print(f"  May 10, 2026: {may:,} voters")

# Check if there's a May 2024 or Nov 2023 city election
for date in ['2024-05-04', '2024-11-05', '2023-05-06', '2023-11-07', '2025-05-03', '2025-11-04']:
    cnt = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date = ?", (date,)).fetchone()[0]
    if cnt > 0:
        print(f"  {date}: {cnt:,} voters")

# The May 2, 2026 election included city races (we saw it on the county page)
may2 = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date = '2026-05-02'").fetchone()[0]
print(f"\n  May 2, 2026 (local entities): {may2:,} voters")

conn.close()
