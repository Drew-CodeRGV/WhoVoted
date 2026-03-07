#!/usr/bin/env python3
"""Check D15 Democratic primary votes breakdown"""
import sqlite3

conn = sqlite3.connect('data/whovoted.db')
c = conn.cursor()

print("="*80)
print("D15 (TX-15) DEMOCRATIC PRIMARY VOTES - 2026-03-03")
print("="*80)

# Total Democratic votes in TX-15
c.execute("""
    SELECT COUNT(DISTINCT ve.vuid) 
    FROM voter_elections ve 
    JOIN voters v ON ve.vuid = v.vuid 
    WHERE v.congressional_district = '15' 
    AND ve.election_date = '2026-03-03' 
    AND ve.party_voted = 'Democratic'
""")
dem_total = c.fetchone()[0]
print(f"\nTotal Democratic votes in TX-15: {dem_total:,}")

# Breakdown by county
print("\nBreakdown by county:")
print("-" * 80)
c.execute("""
    SELECT v.county, COUNT(DISTINCT ve.vuid) as votes
    FROM voter_elections ve 
    JOIN voters v ON ve.vuid = v.vuid 
    WHERE v.congressional_district = '15' 
    AND ve.election_date = '2026-03-03' 
    AND ve.party_voted = 'Democratic'
    GROUP BY v.county
    ORDER BY votes DESC
""")
for row in c.fetchall():
    print(f"  {row[0]:20s}: {row[1]:6,} votes")

# Check if there's early voting vs election day data
print("\n" + "="*80)
print("CHECKING FOR EARLY VS ELECTION DAY BREAKDOWN")
print("="*80)

c.execute("PRAGMA table_info(voter_elections)")
columns = [row[1] for row in c.fetchall()]
print(f"\nColumns in voter_elections table:")
for col in columns:
    print(f"  - {col}")

if 'voting_method' in columns or 'vote_type' in columns:
    print("\n✓ Voting method column exists")
    method_col = 'voting_method' if 'voting_method' in columns else 'vote_type'
    
    c.execute(f"""
        SELECT {method_col}, COUNT(DISTINCT ve.vuid) as votes
        FROM voter_elections ve 
        JOIN voters v ON ve.vuid = v.vuid 
        WHERE v.congressional_district = '15' 
        AND ve.election_date = '2026-03-03' 
        AND ve.party_voted = 'Democratic'
        GROUP BY {method_col}
    """)
    print(f"\nBreakdown by {method_col}:")
    print("-" * 80)
    for row in c.fetchall():
        print(f"  {row[0]:20s}: {row[1]:6,} votes")
else:
    print("\n⚠ No voting method column found")
    print("  Cannot distinguish between early voting and election day")

# Check Republican votes for comparison
print("\n" + "="*80)
print("REPUBLICAN PRIMARY VOTES FOR COMPARISON")
print("="*80)

c.execute("""
    SELECT COUNT(DISTINCT ve.vuid) 
    FROM voter_elections ve 
    JOIN voters v ON ve.vuid = v.vuid 
    WHERE v.congressional_district = '15' 
    AND ve.election_date = '2026-03-03' 
    AND ve.party_voted = 'Republican'
""")
rep_total = c.fetchone()[0]
print(f"\nTotal Republican votes in TX-15: {rep_total:,}")

# Total all parties
total_all = dem_total + rep_total
print(f"\nTotal all parties: {total_all:,}")
print(f"  Democratic: {dem_total:,} ({dem_total/total_all*100:.1f}%)")
print(f"  Republican: {rep_total:,} ({rep_total/total_all*100:.1f}%)")

# Check what the cache shows
print("\n" + "="*80)
print("WHAT THE CACHE SHOWS")
print("="*80)

import json
from pathlib import Path

cache_file = Path('/opt/whovoted/public/cache/district_report_TX-15_Congressional_District_(PlanC2333).json')
if cache_file.exists():
    with open(cache_file) as f:
        cache = json.load(f)
    print(f"\nCache file data:")
    print(f"  Total: {cache['total']:,}")
    print(f"  Democratic: {cache['dem']:,}")
    print(f"  Republican: {cache['rep']:,}")
    print(f"  Dem share: {cache['dem_share']}%")
else:
    print("\n✗ Cache file not found")

conn.close()

print("\n" + "="*80)
print("EXPECTED: 54,573 Democratic votes")
print(f"ACTUAL:   {dem_total:,} Democratic votes")
print(f"DIFFERENCE: {54573 - dem_total:,}")
print("="*80)
