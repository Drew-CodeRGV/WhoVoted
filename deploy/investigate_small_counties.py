#!/usr/bin/env python3
"""Investigate the 72 counties with small voter counts in TX-15."""

import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=" * 80)
print("INVESTIGATING SMALL COUNTY COUNTS IN TX-15")
print("=" * 80)

# Get all counties with TX-15 voters
print("\nAll counties with TX-15 voters (voted in 2026):")
print("-" * 80)

counties = conn.execute("""
    SELECT 
        v.county,
        COUNT(*) as count,
        COUNT(DISTINCT v.vuid) as unique_voters,
        MIN(v.lat) as min_lat,
        MAX(v.lat) as max_lat,
        MIN(v.lng) as min_lng,
        MAX(v.lng) as max_lng
    FROM voters v
    JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    GROUP BY v.county
    ORDER BY count DESC
""").fetchall()

print(f"Total counties: {len(counties)}")
print(f"\n{'County':<20} {'Count':>8} {'Lat Range':>20} {'Lng Range':>20}")
print("-" * 80)

# TX-15 should be in South Texas, roughly:
# Latitude: 26.0° to 29.8°N
# Longitude: -98.5° to -96.6°W

hidalgo_count = 0
brooks_count = 0
small_counties = []
wrong_location = []

for county, count, unique, min_lat, max_lat, min_lng, max_lng in counties:
    lat_range = f"{min_lat:.2f} to {max_lat:.2f}" if min_lat and max_lat else "N/A"
    lng_range = f"{min_lng:.2f} to {max_lng:.2f}" if min_lng and max_lng else "N/A"
    
    if county == 'Hidalgo':
        hidalgo_count = count
    elif county == 'Brooks':
        brooks_count = count
    elif count < 526:
        small_counties.append((county, count, min_lat, max_lat, min_lng, max_lng))
        
        # Check if coordinates are outside TX-15 expected range
        if min_lat and max_lat and min_lng and max_lng:
            # TX-15 boundary: 26.0363 to 29.7847 lat, -98.5366 to -96.5606 lng
            if max_lat > 29.8 or min_lat < 26.0 or min_lng < -98.6 or max_lng > -96.5:
                wrong_location.append((county, count, min_lat, max_lat, min_lng, max_lng))
    
    print(f"{county:<20} {count:>8,} {lat_range:>20} {lng_range:>20}")

print(f"\n{'=' * 80}")
print(f"ANALYSIS:")
print(f"{'=' * 80}")
print(f"\nExpected counties in TX-15:")
print(f"  - Hidalgo County (main): {hidalgo_count:,} voters")
print(f"  - Brooks County: {brooks_count:,} voters")
print(f"\nSmall counties (<526 voters): {len(small_counties)}")
print(f"Counties with coordinates outside TX-15 boundary: {len(wrong_location)}")

if wrong_location:
    print(f"\nCounties with WRONG coordinates (outside TX-15 boundary):")
    print("-" * 80)
    for county, count, min_lat, max_lat, min_lng, max_lng in wrong_location[:10]:
        print(f"  {county:<20} {count:>6,} voters")
        print(f"    Lat: {min_lat:.4f} to {max_lat:.4f}")
        print(f"    Lng: {min_lng:.4f} to {max_lng:.4f}")
        
        # Determine where these coordinates actually are
        if max_lat > 30.0:
            print(f"    → This is CENTRAL TEXAS (Austin area), NOT South Texas!")
        elif max_lat > 29.8:
            print(f"    → This is NORTH of TX-15 boundary")
        elif min_lat < 26.0:
            print(f"    → This is SOUTH of TX-15 boundary")

# Sample some voters from wrong counties
print(f"\n{'=' * 80}")
print(f"SAMPLE VOTERS FROM WRONG COUNTIES:")
print(f"{'=' * 80}")

for county, count, _, _, _, _ in wrong_location[:3]:
    print(f"\n{county} County (sample 5 voters):")
    print("-" * 80)
    
    samples = conn.execute("""
        SELECT v.vuid, v.firstname, v.lastname, v.address, v.lat, v.lng
        FROM voters v
        JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.congressional_district = '15'
        AND v.county = ?
        AND ve.election_date = '2026-03-03'
        LIMIT 5
    """, [county]).fetchall()
    
    for vuid, first, last, address, lat, lng in samples:
        print(f"  {first} {last}")
        print(f"    Address: {address or 'N/A'}")
        print(f"    Coords: ({lat:.4f}, {lng:.4f})" if lat and lng else "    Coords: N/A")

conn.close()

print(f"\n{'=' * 80}")
print(f"CONCLUSION:")
print(f"{'=' * 80}")
print(f"These voters have coordinates that place them OUTSIDE the TX-15 boundary.")
print(f"This is a GEOCODING ERROR - their addresses were geocoded to wrong locations.")
print(f"\nOptions:")
print(f"  1. Re-geocode these addresses using a better geocoding service")
print(f"  2. Remove district assignments for voters with coordinates outside boundary")
print(f"  3. Manually verify and correct the addresses")
print(f"{'=' * 80}")
