#!/usr/bin/env python3
"""Fix duplicate district assignments - consolidate TX-15 and 15 into just 15."""

import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=" * 70)
print("FIXING DUPLICATE DISTRICT ASSIGNMENTS")
print("=" * 70)

# Check current state
print("\nCURRENT STATE:")
print("-" * 70)
districts = conn.execute("""
    SELECT congressional_district, COUNT(*) as count
    FROM voters
    WHERE congressional_district IS NOT NULL AND congressional_district != ''
    GROUP BY congressional_district
    ORDER BY count DESC
""").fetchall()

for district, count in districts:
    print(f"  {district:20s}: {count:7,} voters")

# The problem: we have both 'TX-15' and '15', 'TX-28' and '28', 'TX-34' and '34'
# Solution: Standardize to just the number (15, 28, 34)

print("\nFIXING...")
print("-" * 70)

# Update TX-15 -> 15
updated_15 = conn.execute("""
    UPDATE voters
    SET congressional_district = '15'
    WHERE congressional_district = 'TX-15'
""").rowcount
print(f"  Updated TX-15 -> 15: {updated_15:,} voters")

# Update TX-28 -> 28
updated_28 = conn.execute("""
    UPDATE voters
    SET congressional_district = '28'
    WHERE congressional_district = 'TX-28'
""").rowcount
print(f"  Updated TX-28 -> 28: {updated_28:,} voters")

# Update TX-34 -> 34
updated_34 = conn.execute("""
    UPDATE voters
    SET congressional_district = '34'
    WHERE congressional_district = 'TX-34'
""").rowcount
print(f"  Updated TX-34 -> 34: {updated_34:,} voters")

conn.commit()

# Check new state
print("\nNEW STATE:")
print("-" * 70)
districts_after = conn.execute("""
    SELECT congressional_district, COUNT(*) as count
    FROM voters
    WHERE congressional_district IS NOT NULL AND congressional_district != ''
    GROUP BY congressional_district
    ORDER BY count DESC
""").fetchall()

for district, count in districts_after:
    print(f"  {district:20s}: {count:7,} voters")

# Check Hidalgo County specifically
print("\nHIDALGO COUNTY AFTER FIX:")
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

# Overall coverage
total_geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded = 1").fetchone()[0]
has_congressional = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded = 1 AND congressional_district IS NOT NULL AND congressional_district != ''").fetchone()[0]

print(f"\nOVERALL COVERAGE:")
print(f"  Total geocoded voters: {total_geocoded:,}")
print(f"  With Congressional district: {has_congressional:,} ({has_congressional/total_geocoded*100:.1f}%)")
print(f"  Missing Congressional: {total_geocoded - has_congressional:,}")

conn.close()

print("\n" + "=" * 70)
print("NEXT STEP: Regenerate cache files with corrected data")
print("=" * 70)
