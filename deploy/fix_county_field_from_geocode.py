#!/usr/bin/env python3
"""Fix county field based on actual geocoded coordinates."""

import sqlite3
import json
from shapely.geometry import shape, Point

print("=" * 80)
print("FIXING COUNTY FIELD FROM GEOCODED COORDINATES")
print("=" * 80)

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# Load county boundaries (we need a county boundary file)
# For now, let's check if voters in TX-15 with wrong county are actually in Hidalgo

print("\nChecking voters with mismatched county fields...")
print("-" * 80)

# Get voters in TX-15 with non-Hidalgo/Brooks counties
mismatched = conn.execute("""
    SELECT 
        v.vuid,
        v.county,
        v.lat,
        v.lng,
        v.address
    FROM voters v
    WHERE v.congressional_district = '15'
    AND v.geocoded = 1
    AND v.county NOT IN ('Hidalgo', 'Brooks')
    LIMIT 20
""").fetchall()

print(f"Found {len(mismatched)} sample voters with mismatched counties")
print(f"\nSample voters:")
print("-" * 80)

for vuid, county, lat, lng, address in mismatched[:10]:
    print(f"\nVUID: {vuid}")
    print(f"  County in DB: {county}")
    print(f"  Coordinates: ({lat:.4f}, {lng:.4f})")
    print(f"  Address: {address or 'N/A'}")
    
    # Hidalgo County is roughly:
    # Lat: 26.0 to 26.8
    # Lng: -98.5 to -97.8
    if 26.0 <= lat <= 26.8 and -98.5 <= lng <= -97.8:
        print(f"  → Coordinates are in HIDALGO COUNTY range")
    elif 26.2 <= lat <= 27.3 and -98.4 <= lng <= -98.0:
        print(f"  → Coordinates are in BROOKS COUNTY range")
    else:
        print(f"  → Coordinates are OUTSIDE expected TX-15 counties")

# Count how many voters have wrong county field
print(f"\n{'=' * 80}")
print(f"COUNTY MISMATCH STATISTICS:")
print(f"{'=' * 80}")

wrong_county_counts = conn.execute("""
    SELECT 
        v.county,
        COUNT(*) as count
    FROM voters v
    WHERE v.congressional_district = '15'
    AND v.geocoded = 1
    AND v.county NOT IN ('Hidalgo', 'Brooks')
    GROUP BY v.county
    ORDER BY count DESC
""").fetchall()

total_wrong = sum(count for _, count in wrong_county_counts)
print(f"\nTotal voters with wrong county field: {total_wrong:,}")
print(f"\nBreakdown:")
for county, count in wrong_county_counts[:20]:
    print(f"  {county:20s}: {count:6,} voters")

# Check if we can fix this by looking at coordinates
print(f"\n{'=' * 80}")
print(f"PROPOSED FIX:")
print(f"{'=' * 80}")
print(f"\nOption 1: Use reverse geocoding API to get correct county from coordinates")
print(f"Option 2: Use county boundary files to determine county from coordinates")
print(f"Option 3: Accept that county field may be wrong and show 'Location-based' instead")
print(f"\nFor now, let's check if these are all actually in Hidalgo...")

# Check if all wrong-county voters are in Hidalgo coordinate range
in_hidalgo_range = conn.execute("""
    SELECT COUNT(*)
    FROM voters v
    WHERE v.congressional_district = '15'
    AND v.geocoded = 1
    AND v.county NOT IN ('Hidalgo', 'Brooks')
    AND v.lat BETWEEN 26.0 AND 26.8
    AND v.lng BETWEEN -98.5 AND -97.8
""").fetchone()[0]

in_brooks_range = conn.execute("""
    SELECT COUNT(*)
    FROM voters v
    WHERE v.congressional_district = '15'
    AND v.geocoded = 1
    AND v.county NOT IN ('Hidalgo', 'Brooks')
    AND v.lat BETWEEN 26.2 AND 27.3
    AND v.lng BETWEEN -98.4 AND -98.0
""").fetchone()[0]

print(f"\nVoters with wrong county but coordinates in Hidalgo range: {in_hidalgo_range:,}")
print(f"Voters with wrong county but coordinates in Brooks range: {in_brooks_range:,}")

if in_hidalgo_range + in_brooks_range == total_wrong:
    print(f"\n✓ ALL voters with wrong county are actually in Hidalgo/Brooks!")
    print(f"  We can safely update their county field based on coordinates.")
else:
    print(f"\n⚠ Some voters have coordinates outside Hidalgo/Brooks range")
    print(f"  Need more investigation before updating county field.")

conn.close()

print(f"\n{'=' * 80}")
