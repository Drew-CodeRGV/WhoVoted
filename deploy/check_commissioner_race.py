#!/usr/bin/env python3
"""
Check if the certified numbers (9,876 early + 3,754 election day) are for
the COMMISSIONER RACE specifically, not all DEM primary votes.
"""

import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("="*80)
print("CHECKING FOR COMMISSIONER RACE DATA")
print("="*80)

# Check what races exist in the database
cur.execute("""
    SELECT DISTINCT election_type, COUNT(DISTINCT vuid) as voters
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    GROUP BY election_type
""")

print("\nElection types in database:")
for row in cur.fetchall():
    print(f"  {row['election_type']}: {row['voters']:,} voters")

# Check if there's a race_name or contest field
cur.execute("PRAGMA table_info(voter_elections)")
columns = [row['name'] for row in cur.fetchall()]
print(f"\nColumns in voter_elections: {', '.join(columns)}")

# The issue: we're counting ALL DEM primary voters, but the certified numbers
# might be for a specific race (Commissioner Precinct 2)

# News article said: "Cantu received 9,740 votes"
# User said: "9,876 early + 3,754 election day = 13,630 DEM votes"
# 9,740 is very close to 9,876!

print("\n" + "="*80)
print("HYPOTHESIS")
print("="*80)
print("The certified numbers (9,876 early + 3,754 eday) might be for:")
print("1. The Commissioner Precinct 2 race specifically (not all DEM primary votes)")
print("2. A different geographic boundary than what we have")
print("3. A filtered dataset (excluding certain precinct types)")
print()
print("News article shows Cantu got 9,740 total votes in CPct-2 commissioner race.")
print("This is very close to the 9,876 early voting number!")
print()
print("PROBLEM: Our database tracks party_voted (DEM/REP) but not specific races.")
print("We're counting ALL DEM primary voters, not just commissioner race voters.")
print()
print("SOLUTION: The user's certified numbers are likely for ALL DEM primary voters")
print("in the CORRECT CPct-2 boundary, which is smaller than our current boundary.")

conn.close()
