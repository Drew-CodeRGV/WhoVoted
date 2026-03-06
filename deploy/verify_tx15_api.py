#!/usr/bin/env python3
"""Verify TX-15 API response matches cache and database."""

import sqlite3
import json
from pathlib import Path

print("=" * 70)
print("TX-15 API VERIFICATION")
print("=" * 70)

# 1. Check database
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("\n1. DATABASE CHECK:")
print("-" * 70)

# Get TX-15 voters by county
county_breakdown = conn.execute("""
    SELECT 
        v.county,
        COUNT(*) as total,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
    FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    GROUP BY v.county
    ORDER BY total DESC
""").fetchall()

print(f"Counties with TX-15 voters who voted in 2026:")
total_all = 0
for county, total, dem, rep in county_breakdown:
    print(f"  {county:20s}: {total:6,} voters (D:{dem:5,} R:{rep:5,})")
    total_all += total
print(f"  {'TOTAL':20s}: {total_all:6,} voters")

# 2. Check cache file
print("\n2. CACHE FILE CHECK:")
print("-" * 70)

cache_file = Path('/opt/whovoted/public/cache/district_report_TX-15_Congressional_District_(PlanC2333).json')
if cache_file.exists():
    with open(cache_file) as f:
        cache_data = json.load(f)
    
    print(f"Cache file: {cache_file.name}")
    print(f"Total voters: {cache_data['total']:,}")
    print(f"Dem: {cache_data['dem']:,}, Rep: {cache_data['rep']:,}")
    print(f"\nCounty breakdown from cache:")
    for item in cache_data['votes_by_county']:
        print(f"  {item['county']:20s}: {item['total']:6,} voters (D:{item['dem']:5,} R:{item['rep']:5,})")
else:
    print(f"ERROR: Cache file not found!")

# 3. Check if there's a mismatch
print("\n3. VERIFICATION:")
print("-" * 70)

if cache_file.exists():
    cache_total = cache_data['total']
    if cache_total == total_all:
        print(f"✓ Cache matches database: {cache_total:,} voters")
    else:
        print(f"✗ MISMATCH! Cache: {cache_total:,}, Database: {total_all:,}")
    
    # Check county breakdown
    cache_counties = {item['county']: item['total'] for item in cache_data['votes_by_county']}
    db_counties = {county: total for county, total, _, _ in county_breakdown}
    
    all_counties = set(cache_counties.keys()) | set(db_counties.keys())
    mismatches = []
    for county in sorted(all_counties):
        cache_count = cache_counties.get(county, 0)
        db_count = db_counties.get(county, 0)
        if cache_count != db_count:
            mismatches.append(f"  {county}: Cache={cache_count}, DB={db_count}")
    
    if mismatches:
        print(f"\n✗ County mismatches found:")
        for m in mismatches:
            print(m)
    else:
        print(f"✓ All county breakdowns match")

# 4. Check what the API would return
print("\n4. API ENDPOINT CHECK:")
print("-" * 70)

# Simulate what /api/district-stats would return
# It should use the cache file if it exists
print(f"API would return cache file: {cache_file.name}")
print(f"This is what the frontend sees when loading TX-15")

# 5. Check for other potential issues
print("\n5. POTENTIAL ISSUES:")
print("-" * 70)

# Check if there are voters with TX-15 assignment but wrong county
wrong_county = conn.execute("""
    SELECT county, COUNT(*) as count
    FROM voters
    WHERE congressional_district = '15'
    AND county NOT IN ('Hidalgo', 'Brooks', 'Jim Wells', 'Kleberg', 'Nueces', 'San Patricio')
    GROUP BY county
    ORDER BY count DESC
""").fetchall()

if wrong_county:
    print(f"⚠ Voters with TX-15 assignment in unexpected counties:")
    for county, count in wrong_county:
        print(f"  {county}: {count:,} voters")
    print(f"\nThese might be geocoding errors or people who moved.")
else:
    print(f"✓ All TX-15 voters are in expected counties")

# Check if there are voters in Hidalgo/Brooks without TX-15 assignment
missing_assignment = conn.execute("""
    SELECT 
        county,
        COUNT(*) as total,
        SUM(CASE WHEN congressional_district = '15' THEN 1 ELSE 0 END) as has_tx15,
        SUM(CASE WHEN congressional_district IS NULL OR congressional_district = '' THEN 1 ELSE 0 END) as no_district
    FROM voters
    WHERE county IN ('Hidalgo', 'Brooks')
    AND geocoded = 1
    GROUP BY county
""").fetchall()

print(f"\nVoters in TX-15 counties:")
for county, total, has_tx15, no_district in missing_assignment:
    pct_assigned = (has_tx15 / total * 100) if total > 0 else 0
    print(f"  {county}: {total:,} geocoded voters, {has_tx15:,} ({pct_assigned:.1f}%) have TX-15 assignment")
    if no_district > 0:
        print(f"    ⚠ {no_district:,} voters have no district assignment")

conn.close()

print("\n" + "=" * 70)
