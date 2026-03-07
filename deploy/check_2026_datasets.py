#!/usr/bin/env python3
"""Check what datasets exist for 2026-03-03 election"""
import sqlite3
import os
from pathlib import Path

conn = sqlite3.connect('data/whovoted.db')
c = conn.cursor()

print("="*80)
print("CHECKING 2026-03-03 ELECTION DATASETS")
print("="*80)

# Check source files
print("\nSource files in voter_elections:")
print("-" * 80)
c.execute("""
    SELECT source_file, COUNT(DISTINCT vuid) as voters
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    GROUP BY source_file
    ORDER BY voters DESC
    LIMIT 20
""")

for row in c.fetchall():
    source = row[0] if row[0] else 'NULL'
    print(f"  {source[:60]:60s}: {row[1]:,} voters")

# Check what files exist in uploads directory
print("\n" + "="*80)
print("FILES IN UPLOADS DIRECTORY")
print("="*80)

uploads_dir = Path('/opt/whovoted/uploads')
if uploads_dir.exists():
    files = list(uploads_dir.glob('*'))
    print(f"\nFound {len(files)} files in uploads/")
    for f in sorted(files)[:20]:
        size = f.stat().st_size / (1024*1024)  # MB
        print(f"  {f.name[:60]:60s}: {size:8.2f} MB")
else:
    print("\nUploads directory not found")

# Check for Hidalgo County specific files
print("\n" + "="*80)
print("HIDALGO COUNTY DATA FOR 2026-03-03")
print("="*80)

c.execute("""
    SELECT source_file, data_source, COUNT(DISTINCT ve.vuid) as voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY source_file, data_source
    ORDER BY voters DESC
""")

print("\nHidalgo Dem voters by source:")
print("-" * 80)
total_hidalgo = 0
for row in c.fetchall():
    source_file = row[0] if row[0] else 'NULL'
    data_source = row[1] if row[1] else 'NULL'
    voters = row[2]
    total_hidalgo += voters
    print(f"  {source_file[:40]:40s} ({data_source:15s}): {voters:,} voters")

print(f"\nTotal Hidalgo Dem voters: {total_hidalgo:,}")

# Official Hidalgo results
print("\n" + "="*80)
print("COMPARISON TO OFFICIAL RESULTS")
print("="*80)

print("\nOfficial D15 Dem total:    54,573")
print(f"Database D15 Dem total:    49,330")
print(f"Missing:                    5,243 (9.6%)")
print(f"\nHidalgo Dem in TX-15:      41,671")
print(f"Other counties in TX-15:    7,659")

conn.close()

print("\n" + "="*80)
print("RECOMMENDATION")
print("="*80)
print("\nThe missing 5,243 voters are likely:")
print("  1. In voter files not yet imported to the database")
print("  2. In the 'uploads' directory waiting to be processed")
print("  3. Need to be scraped from official sources")
print("\nCheck the uploads directory and import any pending files.")
