#!/usr/bin/env python3
"""
Check if D15 voters are in the correct counties
D15 includes: Hidalgo (full), Cameron (full), Willacy (full), plus parts of other counties
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

# D15 counties (9 full + 2 partial)
D15_FULL_COUNTIES = ['Hidalgo', 'Cameron', 'Willacy', 'Brooks', 'Jim Hogg', 'Kenedy', 'Kleberg', 'Starr', 'Zapata']
D15_PARTIAL_COUNTIES = ['Nueces', 'Webb']

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("="*80)
print("D15 COUNTY ANALYSIS")
print("="*80)

# D15 Dem voters by county
print("\nD15 Democratic voters by county:")
cursor.execute("""
    SELECT 
        v.county,
        COUNT(DISTINCT ve.vuid) as voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY v.county
    ORDER BY voters DESC
""")

total_by_county = 0
for county, voters in cursor.fetchall():
    in_d15 = "✓" if county in D15_FULL_COUNTIES else ("~" if county in D15_PARTIAL_COUNTIES else "✗")
    print(f"  {in_d15} {county:<20} {voters:>8,}")
    total_by_county += voters

print(f"\nTotal: {total_by_county:,}")
print(f"Expected: 54,573")
print(f"Difference: {total_by_county - 54573:,}")

# Check if there are voters with NULL county
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    AND (v.county IS NULL OR v.county = '')
""")
null_county = cursor.fetchone()[0]
if null_county > 0:
    print(f"\n⚠ Found {null_county:,} voters with NULL/empty county")

# Check official SOS data only
print("\n" + "-"*80)
print("USING ONLY OFFICIAL TX-SOS DATA")
print("-"*80)
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    AND ve.data_source IN ('tx-sos-evr', 'tx-sos-election-day')
""")
sos_only = cursor.fetchone()[0]
print(f"D15 Dem voters (SOS data only): {sos_only:,}")
print(f"Expected: 54,573")
print(f"Difference: {sos_only - 54573:,}")

conn.close()

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
