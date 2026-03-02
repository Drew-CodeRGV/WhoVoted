#!/usr/bin/env python3
"""Investigate the remaining 13-vote discrepancy."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("="*70)
print("INVESTIGATING REMAINING DISCREPANCY")
print("="*70)

# Check votes without Hidalgo county
no_county = conn.execute("""
    SELECT COUNT(*) as cnt
    FROM voter_elections ve
    LEFT JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND (v.county IS NULL OR v.county = '' OR v.county != 'Hidalgo')
""").fetchone()['cnt']

print(f"\nVotes without Hidalgo county assignment: {no_county:,}")

# Check if these are the missing votes
if no_county > 0:
    party_breakdown = conn.execute("""
        SELECT 
            ve.party_voted,
            COUNT(*) as cnt
        FROM voter_elections ve
        LEFT JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
          AND (v.county IS NULL OR v.county = '' OR v.county != 'Hidalgo')
        GROUP BY ve.party_voted
    """).fetchall()
    
    print("\nParty breakdown of votes without Hidalgo county:")
    for row in party_breakdown:
        print(f"  {row['party_voted']}: {row['cnt']:,}")

# Total votes in database (all counties)
all_votes = conn.execute("""
    SELECT 
        SUM(CASE WHEN party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN party_voted = 'Republican' THEN 1 ELSE 0 END) as rep,
        COUNT(*) as total
    FROM voter_elections
    WHERE election_date = '2026-03-03'
""").fetchone()

print(f"\nTotal votes in database (all counties):")
print(f"  Democratic: {all_votes['dem']:,}")
print(f"  Republican: {all_votes['rep']:,}")
print(f"  Total: {all_votes['total']:,}")

# Hidalgo-only votes
hidalgo_votes = conn.execute("""
    SELECT 
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep,
        COUNT(*) as total
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND v.county = 'Hidalgo'
""").fetchone()

print(f"\nHidalgo County votes only:")
print(f"  Democratic: {hidalgo_votes['dem']:,}")
print(f"  Republican: {hidalgo_votes['rep']:,}")
print(f"  Total: {hidalgo_votes['total']:,}")

print(f"\nOfficial totals:")
print(f"  Democratic: 49,664")
print(f"  Republican: 13,217")
print(f"  Total: 62,881")

# If we include the non-Hidalgo votes
if no_county > 0:
    adjusted_dem = all_votes['dem']
    adjusted_rep = all_votes['rep']
    adjusted_total = all_votes['total']
    
    print(f"\nIf we include votes without county assignment:")
    print(f"  Democratic: {adjusted_dem:,}")
    print(f"  Republican: {adjusted_rep:,}")
    print(f"  Total: {adjusted_total:,}")
    
    print(f"\nDifference from official:")
    print(f"  Democratic: {adjusted_dem - 49664:+,}")
    print(f"  Republican: {adjusted_rep - 13217:+,}")
    print(f"  Total: {adjusted_total - 62881:+,}")

conn.close()

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("""
The remaining discrepancy is likely due to:
1. VUIDs in the roster files that don't exist in the voters table
2. VUIDs that exist but don't have Hidalgo County assigned
3. Minor data processing differences between the PDF and Excel files

To achieve 100% accuracy, we need to:
1. Ensure all VUIDs from the roster files are in the voters table
2. Assign Hidalgo County to any VUIDs that are missing it
3. Verify the official PDF totals match the Excel file totals exactly
""")
