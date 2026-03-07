#!/usr/bin/env python3
"""Check how Hidalgo County is split between districts"""
import sqlite3

conn = sqlite3.connect('data/whovoted.db')
c = conn.cursor()

print("="*80)
print("HIDALGO COUNTY DISTRICT SPLIT")
print("="*80)

c.execute("""
    SELECT congressional_district, COUNT(*) as voters
    FROM voters 
    WHERE county = 'Hidalgo'
    GROUP BY congressional_district 
    ORDER BY voters DESC
""")

print("\nHidalgo County voters by district (all registered):")
print("-" * 80)
for row in c.fetchall():
    district = row[0] if row[0] else 'NULL'
    print(f"  TX-{district}: {row[1]:,} voters")

# Check who voted Dem in 2026-03-03
print("\n" + "="*80)
print("HIDALGO DEMOCRATIC VOTES IN 2026-03-03 PRIMARY")
print("="*80)

c.execute("""
    SELECT v.congressional_district, COUNT(DISTINCT ve.vuid) as votes
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY v.congressional_district
    ORDER BY votes DESC
""")

print("\nHidalgo Dem votes by district:")
print("-" * 80)
total = 0
for row in c.fetchall():
    district = row[0] if row[0] else 'NULL'
    votes = row[1]
    total += votes
    print(f"  TX-{district}: {votes:,} votes")

print(f"\nTotal: {total:,} votes")

# The issue: Hidalgo is split, but we need precinct-level data
print("\n" + "="*80)
print("SOLUTION NEEDED")
print("="*80)
print("\nHidalgo County is split between TX-15 and TX-28.")
print("The district assignment used county-level fallback,")
print("which assigned some voters to the wrong district.")
print("\nWe need to use PRECINCT-level data to correctly assign")
print("Hidalgo County voters to TX-15 vs TX-28.")

conn.close()
