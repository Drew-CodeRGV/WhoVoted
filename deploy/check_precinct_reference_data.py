#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM precinct_districts WHERE state_house_district IS NOT NULL")
print(f"House precincts in reference: {cursor.fetchone()[0]:,}")

cursor.execute("SELECT COUNT(*) FROM precinct_districts WHERE state_senate_district IS NOT NULL")
print(f"Senate precincts in reference: {cursor.fetchone()[0]:,}")

cursor.execute("SELECT COUNT(*) FROM precinct_normalized WHERE state_house_district IS NOT NULL")
print(f"House in normalized table: {cursor.fetchone()[0]:,}")

cursor.execute("SELECT COUNT(*) FROM precinct_normalized WHERE state_senate_district IS NOT NULL")
print(f"Senate in normalized table: {cursor.fetchone()[0]:,}")

# Sample
cursor.execute("SELECT county, precinct, state_house_district, state_senate_district FROM precinct_districts WHERE state_house_district IS NOT NULL LIMIT 5")
print("\nSample precinct_districts:")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
