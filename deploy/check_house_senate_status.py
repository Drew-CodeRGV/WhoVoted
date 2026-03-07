#!/usr/bin/env python3
"""Check current status of House and Senate district assignments"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("=" * 80)
print("HOUSE AND SENATE DISTRICT ASSIGNMENT STATUS")
print("=" * 80)

# Check House districts
cursor.execute("""
    SELECT COUNT(*) FROM voter_elections 
    WHERE election_date = ? AND state_house_district IS NOT NULL AND state_house_district != ''
""", (ELECTION_DATE,))
house_assigned = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT state_house_district) FROM voter_elections 
    WHERE election_date = ? AND state_house_district IS NOT NULL AND state_house_district != ''
""", (ELECTION_DATE,))
house_districts = cursor.fetchone()[0]

# Check Senate districts
cursor.execute("""
    SELECT COUNT(*) FROM voter_elections 
    WHERE election_date = ? AND state_senate_district IS NOT NULL AND state_senate_district != ''
""", (ELECTION_DATE,))
senate_assigned = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT state_senate_district) FROM voter_elections 
    WHERE election_date = ? AND state_senate_district IS NOT NULL AND state_senate_district != ''
""", (ELECTION_DATE,))
senate_districts = cursor.fetchone()[0]

# Total records
cursor.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = ?", (ELECTION_DATE,))
total = cursor.fetchone()[0]

print(f"\nState House Districts:")
print(f"  Assigned voters:     {house_assigned:>10,} ({100*house_assigned/total:.1f}%)")
print(f"  Unique districts:    {house_districts:>10}")

print(f"\nState Senate Districts:")
print(f"  Assigned voters:     {senate_assigned:>10,} ({100*senate_assigned/total:.1f}%)")
print(f"  Unique districts:    {senate_districts:>10}")

print(f"\nTotal voting records:  {total:>10,}")

# Check precinct_districts table
cursor.execute("SELECT COUNT(*) FROM precinct_districts WHERE state_house_district IS NOT NULL")
house_precincts = cursor.fetchone()[0]

cursor.execute("SELECT COUNT(*) FROM precinct_districts WHERE state_senate_district IS NOT NULL")
senate_precincts = cursor.fetchone()[0]

print(f"\nPrecinct Reference Data:")
print(f"  House precincts:     {house_precincts:>10,}")
print(f"  Senate precincts:    {senate_precincts:>10,}")

conn.close()
