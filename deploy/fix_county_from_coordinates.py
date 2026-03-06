#!/usr/bin/env python3
"""Fix county field for TX-15 voters based on their geocoded coordinates."""

import sqlite3

print("=" * 80)
print("FIXING COUNTY FIELD FOR TX-15 VOTERS")
print("=" * 80)

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# Create backup
print("\n1. Creating backup...")
conn.execute("DROP TABLE IF EXISTS voters_county_backup_20260305")
conn.execute("CREATE TABLE voters_county_backup_20260305 AS SELECT vuid, county FROM voters WHERE congressional_district = '15'")
backup_count = conn.execute("SELECT COUNT(*) FROM voters_county_backup_20260305").fetchone()[0]
print(f"✓ Backed up {backup_count:,} voter county fields")

# Fix county field based on coordinates
print("\n2. Fixing county field based on coordinates...")
print("-" * 80)

# Hidalgo County range: 26.0 to 26.8 lat, -98.5 to -97.8 lng
hidalgo_updated = conn.execute("""
    UPDATE voters
    SET county = 'Hidalgo'
    WHERE congressional_district = '15'
    AND geocoded = 1
    AND lat BETWEEN 26.0 AND 26.8
    AND lng BETWEEN -98.5 AND -97.8
    AND county != 'Hidalgo'
""").rowcount

print(f"✓ Updated {hidalgo_updated:,} voters to Hidalgo County")

# Brooks County range: 26.2 to 27.3 lat, -98.4 to -98.0 lng
brooks_updated = conn.execute("""
    UPDATE voters
    SET county = 'Brooks'
    WHERE congressional_district = '15'
    AND geocoded = 1
    AND lat BETWEEN 26.2 AND 27.3
    AND lng BETWEEN -98.4 AND -98.0
    AND county != 'Brooks'
    AND county != 'Hidalgo'
""").rowcount

print(f"✓ Updated {brooks_updated:,} voters to Brooks County")

conn.commit()

# Verify results
print("\n3. Verification:")
print("-" * 80)

counties_after = conn.execute("""
    SELECT 
        v.county,
        COUNT(*) as count
    FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    GROUP BY v.county
    ORDER BY count DESC
""").fetchall()

print(f"\nCounty breakdown after fix (voted in 2026):")
for county, count in counties_after:
    print(f"  {county:20s}: {count:6,} voters")

total_counties = len(counties_after)
print(f"\nTotal counties: {total_counties}")

if total_counties <= 3:
    print(f"✓ SUCCESS: County field fixed! Now showing only actual TX-15 counties.")
else:
    print(f"⚠ Still have {total_counties} counties. May need more investigation.")

conn.close()

print(f"\n{'=' * 80}")
print(f"COUNTY FIX COMPLETE")
print(f"{'=' * 80}")
