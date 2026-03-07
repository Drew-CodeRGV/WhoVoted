#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cursor = conn.cursor()

d15_counties = ['Hidalgo', 'Brooks', 'Jim Wells', 'Bee', 'San Patricio', 'Refugio']

print("Checking precinct mappings for D15 counties:\n")

for county in d15_counties:
    cursor.execute("""
        SELECT COUNT(*) FROM precinct_districts 
        WHERE county = ? AND congressional_district = '15'
    """, (county,))
    count = cursor.fetchone()[0]
    print(f"{county:<20} {count:>6} precinct mappings")

print("\nChecking what districts ARE in precinct_districts:")
cursor.execute("""
    SELECT DISTINCT congressional_district, COUNT(*) as count
    FROM precinct_districts
    WHERE congressional_district IS NOT NULL
    GROUP BY congressional_district
    ORDER BY congressional_district
""")

for dist, count in cursor.fetchall():
    print(f"  District {dist}: {count} precincts")

conn.close()
