#!/usr/bin/env python3
"""Check TX-15 numbers to understand the discrepancy."""

import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=" * 60)
print("TX-15 DISTRICT NUMBERS CHECK")
print("=" * 60)

# Total voters with TX-15 assignment
total_assigned = conn.execute("""
    SELECT COUNT(*) FROM voters 
    WHERE congressional_district = '15'
""").fetchone()[0]

print(f"\n1. Total voters with TX-15 assignment: {total_assigned:,}")

# Voters with TX-15 AND voted in 2026
voted_2026 = conn.execute("""
    SELECT COUNT(*) 
    FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
""").fetchone()[0]

print(f"2. Voters with TX-15 AND voted in 2026: {voted_2026:,}")

# Breakdown by county (TX-15 assigned)
print(f"\n3. Breakdown by county (TX-15 assigned):")
county_rows = conn.execute("""
    SELECT county, COUNT(*) as count
    FROM voters
    WHERE congressional_district = '15'
    GROUP BY county
    ORDER BY count DESC
    LIMIT 10
""").fetchall()

for county, count in county_rows:
    print(f"   {county}: {count:,}")

# Check what the cache file shows
import json
from pathlib import Path

cache_file = Path('/opt/whovoted/public/cache/district_report_TX-15_Congressional_District_(PlanC2333).json')
if cache_file.exists():
    with open(cache_file) as f:
        cache_data = json.load(f)
    print(f"\n4. Cache file shows: {cache_data['total']:,} voters")
    print(f"   Cache breakdown:")
    for item in cache_data['votes_by_county'][:5]:
        print(f"   {item['county']}: {item['total']:,}")
else:
    print(f"\n4. Cache file not found at: {cache_file}")

# Check voter_elections table for TX-15 voters
print(f"\n5. Checking voter_elections records for TX-15 voters:")
election_breakdown = conn.execute("""
    SELECT ve.election_date, COUNT(*) as count
    FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.congressional_district = '15'
    GROUP BY ve.election_date
    ORDER BY ve.election_date DESC
""").fetchall()

for election_date, count in election_breakdown:
    print(f"   {election_date}: {count:,} voters")

print("\n" + "=" * 60)
print("ANALYSIS")
print("=" * 60)

if total_assigned > voted_2026:
    print(f"\nThe cache shows {voted_2026:,} voters because it only counts")
    print(f"voters who ACTUALLY VOTED in the 2026-03-03 election.")
    print(f"\nThere are {total_assigned:,} total registered voters in TX-15,")
    print(f"but only {voted_2026:,} of them voted in 2026.")
    print(f"\nTurnout: {voted_2026/total_assigned*100:.1f}%")
    
    print(f"\n\nQUESTION FOR USER:")
    print(f"Should the district report show:")
    print(f"  A) All {total_assigned:,} registered voters in TX-15?")
    print(f"  B) Only the {voted_2026:,} who voted in 2026?")
    print(f"\nCurrently showing: B (only voters who voted)")

conn.close()
