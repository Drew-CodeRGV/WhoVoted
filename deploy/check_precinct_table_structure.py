#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cursor = conn.cursor()

print("precinct_districts table structure:")
cursor.execute("PRAGMA table_info(precinct_districts)")
for row in cursor.fetchall():
    print(f"  {row}")

print("\nSample data:")
cursor.execute("SELECT * FROM precinct_districts LIMIT 5")
for row in cursor.fetchall():
    print(f"  {row}")

conn.close()
