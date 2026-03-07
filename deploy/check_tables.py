#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = [row[0] for row in cursor.fetchall()]
print("Tables in database:")
for table in tables:
    print(f"  {table}")
    if 'precinct' in table.lower() or 'district' in table.lower():
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]
        print(f"    -> {count:,} rows")
conn.close()
