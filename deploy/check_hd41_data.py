#!/usr/bin/env python3
"""Quick check: what district data exists for HD-41."""
import sqlite3

DB = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB)

# Check district columns
cols = conn.execute('PRAGMA table_info(voters)').fetchall()
district_cols = [col[1] for col in cols if 'district' in col[1].lower()]
print("District columns:", district_cols)

for name in district_cols:
    cnt = conn.execute(f"SELECT COUNT(*) FROM voters WHERE {name} IS NOT NULL AND {name} != ''").fetchone()[0]
    sample = conn.execute(f"SELECT DISTINCT {name} FROM voters WHERE {name} IS NOT NULL AND {name} != '' LIMIT 10").fetchall()
    print(f"  {name}: {cnt} rows, samples: {[s[0] for s in sample]}")

# Check if there's a '41' anywhere
for name in district_cols:
    cnt41 = conn.execute(f"SELECT COUNT(*) FROM voters WHERE {name} LIKE '%41%'").fetchone()[0]
    if cnt41 > 0:
        sample41 = conn.execute(f"SELECT DISTINCT {name} FROM voters WHERE {name} LIKE '%41%' LIMIT 5").fetchall()
        print(f"  ** {name} has {cnt41} rows with '41': {[s[0] for s in sample41]}")

# Check election dates
print("\nElection dates in voter_elections:")
dates = conn.execute("SELECT DISTINCT election_date, COUNT(*) as cnt FROM voter_elections GROUP BY election_date ORDER BY election_date DESC LIMIT 10").fetchall()
for d, cnt in dates:
    print(f"  {d}: {cnt} votes")

conn.close()
