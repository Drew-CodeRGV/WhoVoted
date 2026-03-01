#!/usr/bin/env python3
"""Test the elections query directly."""
import sqlite3, time

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db', timeout=300)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")
conn.execute("PRAGMA cache_size=-64000")

print("Testing optimized get_election_datasets query...")
start = time.time()
rows = conn.execute("""
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
    ORDER BY ve.election_date DESC, ve.party_voted, ve.voting_method
""").fetchall()
elapsed = time.time() - start
print(f"Query returned {len(rows)} rows in {elapsed:.1f}s")
for r in rows[:15]:
    print(f"  {r['election_date']} {r['county']:15s} {r['party_voted']:12s} {r['voting_method']:15s}: {r['total_voters']:>8,} voters ({r['geocoded_count']:,} geocoded)")

conn.close()
