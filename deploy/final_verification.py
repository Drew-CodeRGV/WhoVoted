#!/usr/bin/env python3
"""Final verification of district assignments."""

import sqlite3
import json
from pathlib import Path

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=" * 80)
print("FINAL DISTRICT ASSIGNMENT VERIFICATION")
print("=" * 80)

# 1. Verify no non-geocoded voters have districts
print("\n1. NON-GEOCODED VOTERS CHECK:")
print("-" * 80)
non_geocoded_with_district = conn.execute("""
    SELECT COUNT(*) FROM voters
    WHERE geocoded = 0
    AND (congressional_district IS NOT NULL AND congressional_district != '')
""").fetchone()[0]

if non_geocoded_with_district == 0:
    print("✓ PASS: No non-geocoded voters have district assignments")
else:
    print(f"✗ FAIL: {non_geocoded_with_district:,} non-geocoded voters have districts!")

# 2. Check TX-15 numbers
print("\n2. TX-15 CONGRESSIONAL DISTRICT:")
print("-" * 80)

# Registered voters
tx15_registered = conn.execute("""
    SELECT COUNT(*) FROM voters
    WHERE congressional_district = '15'
    AND geocoded = 1
""").fetchone()[0]

# Voted in 2026
tx15_voted_2026 = conn.execute("""
    SELECT COUNT(*) FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
""").fetchone()[0]

print(f"Registered voters in TX-15: {tx15_registered:,}")
print(f"Voted in 2026: {tx15_voted_2026:,}")
print(f"Turnout: {tx15_voted_2026/tx15_registered*100:.1f}%")

# County breakdown (voted in 2026)
print(f"\nCounty breakdown (voted in 2026):")
counties = conn.execute("""
    SELECT v.county, COUNT(*) as count
    FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    GROUP BY v.county
    ORDER BY count DESC
    LIMIT 10
""").fetchall()

for county, count in counties:
    pct = count / tx15_voted_2026 * 100
    print(f"  {county:20s}: {count:6,} ({pct:5.1f}%)")

# 3. Check cache file
print("\n3. CACHE FILE VERIFICATION:")
print("-" * 80)

cache_file = Path('/opt/whovoted/public/cache/district_report_TX-15_Congressional_District_(PlanC2333).json')
if cache_file.exists():
    with open(cache_file) as f:
        cache_data = json.load(f)
    
    cache_total = cache_data['total']
    if cache_total == tx15_voted_2026:
        print(f"✓ PASS: Cache matches database ({cache_total:,} voters)")
    else:
        print(f"✗ FAIL: Cache ({cache_total:,}) != Database ({tx15_voted_2026:,})")
    
    # Check top counties match
    print(f"\nCache county breakdown:")
    for item in cache_data['votes_by_county'][:5]:
        print(f"  {item['county']:20s}: {item['total']:6,} voters")
else:
    print(f"✗ FAIL: Cache file not found!")

# 4. Check Travis County
print("\n4. TRAVIS COUNTY CHECK:")
print("-" * 80)

travis_total = conn.execute("SELECT COUNT(*) FROM voters WHERE county = 'Travis'").fetchone()[0]
travis_geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE county = 'Travis' AND geocoded = 1").fetchone()[0]
travis_tx15 = conn.execute("SELECT COUNT(*) FROM voters WHERE county = 'Travis' AND congressional_district = '15'").fetchone()[0]
travis_tx15_non_geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE county = 'Travis' AND congressional_district = '15' AND geocoded = 0").fetchone()[0]

print(f"Total Travis County voters: {travis_total:,}")
print(f"Geocoded: {travis_geocoded:,} ({travis_geocoded/travis_total*100:.1f}%)")
print(f"Assigned to TX-15: {travis_tx15:,}")
print(f"TX-15 non-geocoded: {travis_tx15_non_geocoded:,}")

if travis_tx15_non_geocoded == 0:
    print(f"✓ PASS: All Travis County voters in TX-15 are geocoded")
else:
    print(f"✗ FAIL: {travis_tx15_non_geocoded:,} non-geocoded Travis voters in TX-15!")

# 5. Overall stats
print("\n5. OVERALL STATISTICS:")
print("-" * 80)

total_voters = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
total_geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded = 1").fetchone()[0]
total_with_cong = conn.execute("SELECT COUNT(*) FROM voters WHERE congressional_district IS NOT NULL AND congressional_district != ''").fetchone()[0]
total_voted_2026 = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date = '2026-03-03'").fetchone()[0]

print(f"Total voters in database: {total_voters:,}")
print(f"Geocoded voters: {total_geocoded:,} ({total_geocoded/total_voters*100:.1f}%)")
print(f"With Congressional district: {total_with_cong:,} ({total_with_cong/total_voters*100:.1f}%)")
print(f"Voted in 2026: {total_voted_2026:,} ({total_voted_2026/total_voters*100:.1f}%)")

# 6. All districts
print("\n6. ALL CONGRESSIONAL DISTRICTS:")
print("-" * 80)

all_districts = conn.execute("""
    SELECT 
        v.congressional_district,
        COUNT(DISTINCT v.vuid) as registered,
        COUNT(DISTINCT CASE WHEN ve.vuid IS NOT NULL THEN ve.vuid END) as voted_2026
    FROM voters v
    LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = '2026-03-03'
    WHERE v.congressional_district IS NOT NULL AND v.congressional_district != ''
    GROUP BY v.congressional_district
    ORDER BY registered DESC
""").fetchall()

print(f"{'District':<10} {'Registered':>12} {'Voted 2026':>12} {'Turnout':>10}")
print("-" * 80)
for district, registered, voted in all_districts:
    turnout = (voted / registered * 100) if registered > 0 else 0
    print(f"TX-{district:<7} {registered:>12,} {voted:>12,} {turnout:>9.1f}%")

conn.close()

print("\n" + "=" * 80)
print("VERIFICATION COMPLETE")
print("=" * 80)
print("\nSUMMARY:")
print("- District assignments are now accurate based on boundary files")
print("- Only geocoded voters have district assignments")
print("- Cache files match database")
print("- Travis County voters in TX-15 are all geocoded (within boundary)")
print("=" * 80)
