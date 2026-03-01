#!/usr/bin/env python3
"""Add indexes to speed up common queries after statewide data import."""
import sqlite3, time

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db', timeout=300)
conn.execute("PRAGMA journal_mode=WAL")

indexes = [
    ("idx_voters_county", "CREATE INDEX IF NOT EXISTS idx_voters_county ON voters(county)"),
    ("idx_ve_election_date_party", "CREATE INDEX IF NOT EXISTS idx_ve_election_date_party ON voter_elections(election_date, party_voted, voting_method)"),
    ("idx_ve_vuid_election", "CREATE INDEX IF NOT EXISTS idx_ve_vuid_election ON voter_elections(vuid, election_date)"),
    ("idx_ve_data_source", "CREATE INDEX IF NOT EXISTS idx_ve_data_source ON voter_elections(data_source)"),
]

for name, sql in indexes:
    print(f"Creating {name}...", end=" ", flush=True)
    start = time.time()
    try:
        conn.execute(sql)
        conn.commit()
        elapsed = time.time() - start
        print(f"done ({elapsed:.1f}s)")
    except Exception as e:
        print(f"error: {e}")

conn.close()
print("All indexes created.")
