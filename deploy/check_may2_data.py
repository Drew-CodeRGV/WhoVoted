#!/usr/bin/env python3
"""Quick check: do we have May 2, 2026 election data?"""
import sqlite3
DB = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB)
# Check for May 2 data
for date in ['2026-05-02', '2026-05-2']:
    cnt = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date = ?", (date,)).fetchone()[0]
    if cnt: print(f"{date}: {cnt} voters")
# Check all May dates
rows = conn.execute("SELECT election_date, COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date LIKE '2026-05%' GROUP BY election_date").fetchall()
print("All May 2026 dates:")
for d, c in rows: print(f"  {d}: {c}")
conn.close()
