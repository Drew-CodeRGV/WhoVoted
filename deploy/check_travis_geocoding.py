#!/usr/bin/env python3
"""Check Travis County geocoding status."""

import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=" * 70)
print("TRAVIS COUNTY GEOCODING CHECK")
print("=" * 70)

# Check Travis County voters
travis_stats = conn.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN geocoded = 1 THEN 1 ELSE 0 END) as geocoded,
        SUM(CASE WHEN congressional_district IS NOT NULL AND congressional_district != '' THEN 1 ELSE 0 END) as has_district,
        SUM(CASE WHEN geocoded = 0 AND congressional_district IS NOT NULL AND congressional_district != '' THEN 1 ELSE 0 END) as not_geocoded_but_has_district
    FROM voters
    WHERE county = 'Travis'
""").fetchone()

print(f"\nTravis County:")
print(f"  Total voters: {travis_stats[0]:,}")
print(f"  Geocoded: {travis_stats[1]:,} ({travis_stats[1]/travis_stats[0]*100:.1f}%)")
print(f"  Has district assignment: {travis_stats[2]:,} ({travis_stats[2]/travis_stats[0]*100:.1f}%)")
print(f"  NOT geocoded but HAS district: {travis_stats[3]:,}")

if travis_stats[3] > 0:
    print(f"\n⚠ PROBLEM: {travis_stats[3]:,} Travis County voters have district assignments")
    print(f"  but are NOT geocoded! This should be impossible!")
    
    # Check which districts
    districts = conn.execute("""
        SELECT congressional_district, COUNT(*) as count
        FROM voters
        WHERE county = 'Travis'
        AND geocoded = 0
        AND congressional_district IS NOT NULL
        AND congressional_district != ''
        GROUP BY congressional_district
        ORDER BY count DESC
    """).fetchall()
    
    print(f"\n  Districts assigned to non-geocoded Travis voters:")
    for district, count in districts:
        print(f"    TX-{district}: {count:,} voters")

# Check overall
print(f"\n{'=' * 70}")
print("OVERALL CHECK")
print(f"{'=' * 70}")

overall = conn.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN geocoded = 1 THEN 1 ELSE 0 END) as geocoded,
        SUM(CASE WHEN congressional_district IS NOT NULL AND congressional_district != '' THEN 1 ELSE 0 END) as has_district,
        SUM(CASE WHEN geocoded = 0 AND congressional_district IS NOT NULL AND congressional_district != '' THEN 1 ELSE 0 END) as not_geocoded_but_has_district
    FROM voters
""").fetchone()

print(f"\nAll voters:")
print(f"  Total voters: {overall[0]:,}")
print(f"  Geocoded: {overall[1]:,} ({overall[1]/overall[0]*100:.1f}%)")
print(f"  Has district assignment: {overall[2]:,} ({overall[2]/overall[0]*100:.1f}%)")
print(f"  NOT geocoded but HAS district: {overall[3]:,}")

if overall[3] > 0:
    print(f"\n⚠ CRITICAL: {overall[3]:,} voters have district assignments without geocoding!")
    print(f"  This is the root cause of the problem!")

conn.close()

print("\n" + "=" * 70)
