#!/usr/bin/env python3
"""Add performance indexes to the whovoted DB."""
import sqlite3
import time

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)

indexes = [
    # Composite index for the get_election_datasets GROUP BY
    ("idx_ve_date_method_party", 
     "CREATE INDEX IF NOT EXISTS idx_ve_date_method_party ON voter_elections(election_date, voting_method, party_voted)"),
    
    # Composite index for voter_elections JOIN + filter (covers the main query pattern)
    ("idx_ve_vuid_date",
     "CREATE INDEX IF NOT EXISTS idx_ve_vuid_date ON voter_elections(vuid, election_date)"),
    
    # Composite index for voters county + geocoded (for the JOIN in get_election_datasets)
    ("idx_voters_county_geocoded",
     "CREATE INDEX IF NOT EXISTS idx_voters_county_geocoded ON voters(county, geocoded)"),
    
    # Composite index for voters lat/lng (spatial queries with bounds)
    ("idx_voters_lat_lng",
     "CREATE INDEX IF NOT EXISTS idx_voters_lat_lng ON voters(lat, lng)"),
    
    # Composite for the flip detection subquery
    ("idx_ve_vuid_date_party",
     "CREATE INDEX IF NOT EXISTS idx_ve_vuid_date_party ON voter_elections(vuid, election_date, party_voted)"),
    
    # Covering index for the voters JOIN in /api/voters
    ("idx_voters_county_vuid",
     "CREATE INDEX IF NOT EXISTS idx_voters_county_vuid ON voters(county, vuid)"),
]

for name, sql in indexes:
    t0 = time.time()
    conn.execute(sql)
    elapsed = time.time() - t0
    print(f"  {elapsed*1000:>7.1f}ms  {name}")

conn.commit()

# Run ANALYZE to update query planner statistics
print("\nRunning ANALYZE...")
t0 = time.time()
conn.execute("ANALYZE")
elapsed = time.time() - t0
print(f"  {elapsed*1000:>7.1f}ms  ANALYZE complete")

conn.close()
print("\nDone. Indexes created.")
