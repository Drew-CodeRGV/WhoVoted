#!/usr/bin/env python3
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Check if we have precinct data
cursor.execute("SELECT COUNT(*) as total, COUNT(precinct) as with_precinct FROM voters")
total, with_precinct = cursor.fetchone()

print(f"Total voters: {total:,}")
print(f"Voters with precinct: {with_precinct:,}")
print(f"Percentage: {100 * with_precinct / total:.1f}%")

# Check if we have precinct-to-district mapping
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='precinct_districts'")
has_table = cursor.fetchone()

if has_table:
    cursor.execute("SELECT COUNT(*) FROM precinct_districts")
    count = cursor.fetchone()[0]
    print(f"\nprecinct_districts table exists with {count:,} mappings")
else:
    print("\nprecinct_districts table does NOT exist")

# Sample some precincts
cursor.execute("SELECT DISTINCT precinct FROM voters WHERE precinct IS NOT NULL AND precinct != '' LIMIT 10")
print("\nSample precincts:")
for (precinct,) in cursor.fetchall():
    print(f"  {precinct}")

conn.close()
