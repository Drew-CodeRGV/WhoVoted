#!/usr/bin/env python3
"""Add critical indexes for performance - run this first!"""
import sqlite3
import time

DB_PATH = '/opt/whovoted/data/whovoted.db'

print("Adding critical indexes to database...")
print("=" * 60)

conn = sqlite3.connect(DB_PATH)

indexes = [
    ("idx_voters_coords", "CREATE INDEX IF NOT EXISTS idx_voters_coords ON voters(lat, lng) WHERE geocoded=1"),
    ("idx_voters_address", "CREATE INDEX IF NOT EXISTS idx_voters_address ON voters(address)"),
    ("idx_voters_county_geocoded", "CREATE INDEX IF NOT EXISTS idx_voters_county_geocoded ON voters(county, geocoded)"),
    ("idx_ve_election_party", "CREATE INDEX IF NOT EXISTS idx_ve_election_party ON voter_elections(election_date, party_voted)"),
    ("idx_ve_vuid_date", "CREATE INDEX IF NOT EXISTS idx_ve_vuid_date ON voter_elections(vuid, election_date)"),
    ("idx_ve_date_method", "CREATE INDEX IF NOT EXISTS idx_ve_date_method ON voter_elections(election_date, voting_method)"),
    ("idx_ve_vuid_date_party", "CREATE INDEX IF NOT EXISTS idx_ve_vuid_date_party ON voter_elections(vuid, election_date, party_voted)"),
    ("idx_voters_sex", "CREATE INDEX IF NOT EXISTS idx_voters_sex ON voters(sex)"),
    ("idx_voters_birth_year", "CREATE INDEX IF NOT EXISTS idx_voters_birth_year ON voters(birth_year)"),
    ("idx_voters_county", "CREATE INDEX IF NOT EXISTS idx_voters_county ON voters(county)"),
]

start = time.time()
for name, sql in indexes:
    print(f"  Creating {name}...", end=" ", flush=True)
    t0 = time.time()
    conn.execute(sql)
    print(f"✓ ({time.time()-t0:.1f}s)")

conn.commit()
print("\nRunning ANALYZE to update query planner statistics...")
conn.execute("ANALYZE")
conn.commit()

total = time.time() - start
print(f"\n✅ All indexes created in {total:.1f}s")
print("=" * 60)

conn.close()
