#!/usr/bin/env python3
"""Find duplicate VUIDs in 2026 election."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("Finding duplicate VUIDs for 2026-03-03 election in Hidalgo County...\n")

dupes = conn.execute("""
    SELECT 
        ve.vuid,
        v.county,
        COUNT(*) as vote_count,
        GROUP_CONCAT(ve.party_voted, ', ') as parties,
        GROUP_CONCAT(ve.voting_method, ', ') as methods
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
      AND ve.election_date = '2026-03-03'
    GROUP BY ve.vuid
    HAVING COUNT(*) > 1
""").fetchall()

if dupes:
    print(f"Found {len(dupes)} duplicate VUIDs:\n")
    for row in dupes:
        print(f"VUID: {row['vuid']}")
        print(f"  Vote count: {row['vote_count']}")
        print(f"  Parties: {row['parties']}")
        print(f"  Methods: {row['methods']}")
        print()
else:
    print("No duplicates found!")

# Check if removing duplicates would fix the discrepancy
print("\nIf we count only unique VUIDs (removing duplicates):")
unique = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as unique_voters,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem_votes,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep_votes
    FROM (
        SELECT vuid, party_voted, ROW_NUMBER() OVER (PARTITION BY vuid ORDER BY rowid) as rn
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
          AND ve.election_date = '2026-03-03'
    ) ve
    WHERE rn = 1
""").fetchone()

print(f"  Unique voters: {unique['unique_voters']:,}")
print(f"  Democratic: {unique['dem_votes']:,}")
print(f"  Republican: {unique['rep_votes']:,}")

conn.close()
