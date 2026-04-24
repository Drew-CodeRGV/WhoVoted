#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
schema = conn.execute('PRAGMA table_info(district_counts_cache)').fetchall()
print("district_counts_cache schema:")
for row in schema:
    print(f"  {row[1]} ({row[2]})")
