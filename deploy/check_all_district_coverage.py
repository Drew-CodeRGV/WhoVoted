#!/usr/bin/env python3
"""Check district coverage across all geocoded voters."""

import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=" * 70)
print("DISTRICT COVERAGE ANALYSIS")
print("=" * 70)

# Overall coverage
total_geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded = 1").fetchone()[0]
has_congressional = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded = 1 AND congressional_district IS NOT NULL AND congressional_district != ''").fetchone()[0]
has_state_house = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded = 1 AND state_house_district IS NOT NULL AND state_house_district != ''").fetchone()[0]

print(f"\nOVERALL COVERAGE:")
print(f"  Total geocoded voters: {total_geocoded:,}")
print(f"  With Congressional district: {has_congressional:,} ({has_congressional/total_geocoded*100:.1f}%)")
print(f"  With State House district: {has_state_house:,} ({has_state_house/total_geocoded*100:.1f}%)")
print(f"  Missing Congressional: {total_geocoded - has_congressional:,}")
print(f"  Missing State House: {total_geocoded - has_state_house:,}")

# Congressional district breakdown
print(f"\nCONGRESSIONAL DISTRICTS:")
print("-" * 70)
cong_districts = conn.execute("""
    SELECT 
        congressional_district,
        COUNT(*) as total,
        COUNT(DISTINCT county) as counties
    FROM voters
    WHERE geocoded = 1
    AND congressional_district IS NOT NULL
    AND congressional_district != ''
    GROUP BY congressional_district
    ORDER BY CAST(congressional_district AS INTEGER)
""").fetchall()

for district, total, counties in cong_districts:
    print(f"  TX-{district:2s}: {total:7,} voters across {counties:2d} counties")

# Check Hidalgo County specifically
print(f"\nHIDALGO COUNTY BREAKDOWN:")
print("-" * 70)
hidalgo_districts = conn.execute("""
    SELECT 
        COALESCE(congressional_district, 'NO ASSIGNMENT') as district,
        COUNT(*) as total
    FROM voters
    WHERE county = 'Hidalgo'
    AND geocoded = 1
    GROUP BY congressional_district
    ORDER BY total DESC
""").fetchall()

hidalgo_total = sum(total for _, total in hidalgo_districts)
print(f"  Total geocoded in Hidalgo: {hidalgo_total:,}")
for district, total in hidalgo_districts:
    pct = total / hidalgo_total * 100
    print(f"    {district:20s}: {total:7,} ({pct:5.1f}%)")

# Check which voters voted in 2026 by district
print(f"\nVOTERS WHO VOTED IN 2026 BY DISTRICT:")
print("-" * 70)
voted_2026 = conn.execute("""
    SELECT 
        COALESCE(v.congressional_district, 'NO ASSIGNMENT') as district,
        COUNT(*) as total
    FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.geocoded = 1
    AND ve.election_date = '2026-03-03'
    GROUP BY v.congressional_district
    ORDER BY total DESC
    LIMIT 10
""").fetchall()

for district, total in voted_2026:
    print(f"  {district:20s}: {total:7,} voters")

# Check if the boundary file covers all of Hidalgo
print(f"\nBOUNDARY FILE CHECK:")
print("-" * 70)
print(f"The boundary file (districts.json) contains:")
print(f"  - TX-15, TX-28, TX-34 (Congressional)")
print(f"  - 8 State House districts")
print(f"\nHidalgo County should be covered by TX-15, TX-28, and TX-34.")
print(f"But {hidalgo_districts[0][1]:,} voters have no assignment!")
print(f"\nThis suggests:")
print(f"  1. The boundary polygons don't cover all of Hidalgo County")
print(f"  2. OR there are gaps between the district boundaries")
print(f"  3. OR the geocoding placed voters outside the boundaries")

conn.close()

print("\n" + "=" * 70)
