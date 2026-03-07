#!/usr/bin/env python3
"""Verify D15 total against what we have in database"""
import sqlite3

conn = sqlite3.connect('data/whovoted.db')
c = conn.cursor()

print("="*80)
print("D15 (TX-15) VOTE VERIFICATION")
print("="*80)

print("\nUser expects: 54,573 Democratic votes")
print("Database has: 49,330 Democratic votes")
print("Difference:    5,243 votes")

print("\n" + "="*80)
print("CHECKING ALL COUNTIES IN TX-15")
print("="*80)

# All 11 counties in TX-15
tx15_counties = {
    'Hidalgo': 'partial',
    'Brooks': 'full',
    'Bee': 'full',
    'DeWitt': 'full',
    'Goliad': 'full',
    'Gonzales': 'full',
    'Jim Wells': 'full',
    'Karnes': 'full',
    'Lavaca': 'full',
    'Live Oak': 'full',
    'Aransas': 'partial'
}

print("\nTX-15 Counties (9 full + 2 partial):")
print("-" * 80)

total_dem = 0
total_rep = 0
total_all = 0

for county, coverage in tx15_counties.items():
    # Get Dem votes
    c.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        AND v.congressional_district = '15'
        AND ve.election_date = '2026-03-03'
        AND ve.party_voted = 'Democratic'
    """, [county])
    dem = c.fetchone()[0]
    
    # Get Rep votes
    c.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        AND v.congressional_district = '15'
        AND ve.election_date = '2026-03-03'
        AND ve.party_voted = 'Republican'
    """, [county])
    rep = c.fetchone()[0]
    
    total = dem + rep
    total_dem += dem
    total_rep += rep
    total_all += total
    
    marker = f" ({coverage})" if coverage == 'partial' else ""
    print(f"  {county:20s}{marker:10s}: {dem:5,} Dem, {rep:5,} Rep, {total:5,} total")

print("-" * 80)
print(f"  {'TOTAL':30s}: {total_dem:5,} Dem, {total_rep:5,} Rep, {total_all:5,} total")

print("\n" + "="*80)
print("POSSIBLE EXPLANATIONS FOR DIFFERENCE")
print("="*80)

print(f"\n1. Missing voter data:")
print(f"   If 5,243 voters haven't been imported yet")

print(f"\n2. Different election date:")
print(f"   Expected number might be for a different election")

print(f"\n3. Data source difference:")
print(f"   Official results vs voter file data")

print(f"\n4. Precinct assignments:")
print(f"   Some precincts might be assigned to wrong district")

# Check if there are voters in TX-15 counties not assigned to any district
print("\n" + "="*80)
print("VOTERS IN TX-15 COUNTIES WITH NO DISTRICT")
print("="*80)

for county in tx15_counties.keys():
    c.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        AND v.congressional_district IS NULL
        AND ve.election_date = '2026-03-03'
        AND ve.party_voted = 'Democratic'
    """, [county])
    unassigned = c.fetchone()[0]
    if unassigned > 0:
        print(f"  {county}: {unassigned:,} Dem voters with no district")

conn.close()

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)
print("\nThe database shows 49,330 Democratic votes in TX-15")
print("based on precinct-level district assignments.")
print("\nTo reach 54,573, we would need an additional 5,243 votes.")
print("\nPlease verify:")
print("  1. Is 54,573 the correct expected number?")
print("  2. Is this for the 2026-03-03 primary?")
print("  3. Are there additional voter files to import?")
