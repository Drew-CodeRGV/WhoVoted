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
print("\nCounting only unique VUIDs (one vote per person):")
unique = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as unique_voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
      AND ve.election_date = '2026-03-03'
""").fetchone()

# Count party breakdown for unique voters (take first vote record)
party_counts = conn.execute("""
    WITH first_votes AS (
        SELECT ve.vuid, ve.party_voted, MIN(ve.rowid) as first_rowid
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
          AND ve.election_date = '2026-03-03'
        GROUP BY ve.vuid
    )
    SELECT 
        SUM(CASE WHEN party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
    FROM first_votes
""").fetchone()

print(f"  Unique voters: {unique['unique_voters']:,}")
print(f"  Democratic: {party_counts['dem']:,}")
print(f"  Republican: {party_counts['rep']:,}")
print(f"  Total: {party_counts['dem'] + party_counts['rep']:,}")

print(f"\nOfficial numbers:")
print(f"  Democratic: 49,664")
print(f"  Republican: 13,217")
print(f"  Total: 62,881")

print(f"\nDifference after deduplication:")
print(f"  Democratic: {party_counts['dem'] - 49664:+,}")
print(f"  Republican: {party_counts['rep'] - 13217:+,}")
print(f"  Total: {(party_counts['dem'] + party_counts['rep']) - 62881:+,}")

conn.close()
