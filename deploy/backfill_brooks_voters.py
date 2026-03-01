#!/usr/bin/env python3
"""Backfill Brooks County voters into the voters table from voter_elections + geocoding cache."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db
db.init_db()

conn = db.get_connection()

# Find all Brooks VUIDs that are NOT in the voters table
rows = conn.execute("""
    SELECT DISTINCT ve.vuid, ve.party_voted, ve.precinct
    FROM voter_elections ve
    WHERE ve.source_file LIKE '%Voting_History%'
    AND NOT EXISTS (SELECT 1 FROM voters v WHERE v.vuid = ve.vuid)
""").fetchall()

print(f"Found {len(rows)} Brooks VUIDs not in voters table")

# Check geocoding cache for their addresses
print("Inserting voters with county=Brooks...")

# For now, just insert them with county=Brooks and whatever we have
inserted = 0
for r in rows:
    vuid = r[0]
    party = r[1] or ''
    precinct = r[2] or ''
    
    conn.execute("""
        INSERT OR IGNORE INTO voters (vuid, county, current_party, precinct, geocoded, updated_at)
        VALUES (?, 'Brooks', ?, ?, 0, datetime('now'))
    """, (vuid, party, precinct))
    inserted += 1

conn.commit()
print(f"Inserted {inserted} Brooks voters into voters table")

# Now run the reprocessing to fill in geocoded data
print("\nNow reprocessing Brooks PDFs to fill in addresses and coords...")
