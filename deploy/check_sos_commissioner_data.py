#!/usr/bin/env python3
"""
Check if the original SOS voter files had commissioner district data.
"""

import sqlite3
import os
import glob

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("="*80)
print("CHECKING ORIGINAL DATA SOURCES")
print("="*80)

# Check if there are any CSV files with commissioner data
data_dir = '/opt/whovoted/data'
if os.path.exists(data_dir):
    csv_files = glob.glob(f"{data_dir}/*.csv") + glob.glob(f"{data_dir}/**/*.csv", recursive=True)
    print(f"\nFound {len(csv_files)} CSV files in data directory")
    
    # Check a sample file for column headers
    if csv_files:
        sample_file = csv_files[0]
        print(f"\nSample file: {sample_file}")
        try:
            with open(sample_file, 'r') as f:
                header = f.readline().strip()
                print(f"Columns: {header}")
                
                if 'commissioner' in header.lower() or 'precinct' in header.lower():
                    print("\n✓ Found commissioner/precinct columns in CSV!")
        except Exception as e:
            print(f"Error reading file: {e}")

# Check voter_elections table for any commissioner-related data
cur.execute("PRAGMA table_info(voter_elections)")
ve_columns = [row['name'] for row in cur.fetchall()]
print(f"\nvoter_elections columns: {', '.join(ve_columns)}")

# Check if data_source field has any hints
cur.execute("""
    SELECT DISTINCT data_source, COUNT(*) as cnt
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    GROUP BY data_source
""")

print("\nData sources for 2026-03-03 election:")
for row in cur.fetchall():
    print(f"  {row['data_source']}: {row['cnt']:,} records")

# The county-upload source is the most complete - check what fields it has
print("\n" + "="*80)
print("SOLUTION: Contact Hidalgo County Elections")
print("="*80)
print("\nTo get exact numbers, you need the official precinct-to-commissioner mapping.")
print("\nContact:")
print("  Hidalgo County Elections Department")
print("  Phone: (956) 318-2570")
print("  Address: 213 S. Closner Blvd., Edinburg, TX")
print("\nAsk for:")
print("  1. List of voting precincts in Commissioner Precinct 2")
print("  2. OR: Commissioner precinct boundary shapefile")
print("  3. OR: Voter registration file with commissioner_precinct column")

conn.close()
