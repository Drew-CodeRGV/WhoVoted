#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cur = conn.cursor()

print("district_counts_cache schema:")
cur.execute("PRAGMA table_info(district_counts_cache)")
for row in cur.fetchall():
    print(f"  {row}")

print("\nSample records:")
cur.execute("SELECT * FROM district_counts_cache LIMIT 3")
for row in cur.fetchall():
    print(f"  {row}")

conn.close()
