#!/usr/bin/env python3
"""Build the election_summary table for fast /api/elections queries."""
import sqlite3, time

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db', timeout=300)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA cache_size=-64000")

print("Creating election_summary table...")
conn.execute("""
    CREATE TABLE IF NOT EXISTS election_summary (
        election_date TEXT,
        election_year TEXT,
        election_type TEXT,
        voting_method TEXT,
        party_voted TEXT,
        county TEXT,
        total_voters INTEGER,
        geocoded_count INTEGER,
        last_updated TEXT,
        PRIMARY KEY (election_date, party_voted, voting_method, county)
    )
""")
conn.commit()

print("Populating from voter_elections + voters...")
start = time.time()
conn.execute("DELETE FROM election_summary")
conn.execute("""
    INSERT INTO election_summary
        (election_date, election_year, election_type, voting_method,
         party_voted, county, total_voters, geocoded_count, last_updated)
    SELECT 
        ve.election_date,
        ve.election_year,
        ve.election_type,
        ve.voting_method,
        ve.party_voted,
        v.county,
        COUNT(*) as total_voters,
        SUM(CASE WHEN v.geocoded = 1 THEN 1 ELSE 0 END) as geocoded_count,
        MAX(ve.created_at) as last_updated
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.party_voted != '' AND ve.party_voted IS NOT NULL
    GROUP BY ve.election_date, ve.party_voted, ve.voting_method, v.county
""")
conn.commit()
elapsed = time.time() - start

rows = conn.execute("SELECT COUNT(*) FROM election_summary").fetchone()[0]
print(f"Done: {rows} summary rows in {elapsed:.1f}s")

# Show sample
for r in conn.execute("SELECT * FROM election_summary ORDER BY election_date DESC, county LIMIT 15").fetchall():
    print(f"  {r['election_date']} {r['county']:15s} {r['party_voted']:12s} {r['voting_method']:15s}: {r['total_voters']:>8,}")

conn.close()
