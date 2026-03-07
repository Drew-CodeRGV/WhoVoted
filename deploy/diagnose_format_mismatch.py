#!/usr/bin/env python3
"""Diagnose format mismatches between voters and lookup tables."""

import sqlite3

conn = sqlite3.connect('data/whovoted.db')
cursor = conn.cursor()

print('='*80)
print('DIAGNOSING FORMAT MISMATCH')
print('='*80)

print('\nSample precincts from voters table (Hidalgo County):')
cursor.execute("SELECT DISTINCT precinct FROM voters WHERE county = 'Hidalgo' ORDER BY precinct LIMIT 10")
voter_precincts = [row[0] for row in cursor.fetchall()]
for p in voter_precincts:
    print(f"  Voter: '{p}'")

print('\nSample precincts from lookup table (Hidalgo County):')
cursor.execute("SELECT DISTINCT precinct FROM precinct_district_lookup WHERE county LIKE '%Hidalgo%' ORDER BY precinct LIMIT 10")
lookup_precincts = [row[0] for row in cursor.fetchall()]
for p in lookup_precincts:
    print(f"  Lookup: '{p}'")

print('\nSample county names from voters:')
cursor.execute("SELECT DISTINCT county FROM voters ORDER BY county LIMIT 10")
voter_counties = [row[0] for row in cursor.fetchall()]
for c in voter_counties:
    print(f"  Voter: '{c}'")

print('\nSample county names from lookup:')
cursor.execute("SELECT DISTINCT county FROM precinct_district_lookup ORDER BY county LIMIT 10")
lookup_counties = [row[0] for row in cursor.fetchall()]
for c in lookup_counties:
    print(f"  Lookup: '{c}'")

# Check for exact matches
print('\n' + '='*80)
print('CHECKING FOR MATCHES')
print('='*80)

cursor.execute("""
    SELECT COUNT(*) 
    FROM voters v
    JOIN precinct_district_lookup l 
    ON v.county = l.county AND v.precinct = l.precinct
""")
exact_matches = cursor.fetchone()[0]
print(f"\nExact matches (county + precinct): {exact_matches:,}")

cursor.execute("SELECT COUNT(*) FROM voters")
total = cursor.fetchone()[0]
print(f"Total voters: {total:,}")
print(f"Match rate: {exact_matches/total*100:.2f}%")

conn.close()
