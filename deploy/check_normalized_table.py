#!/usr/bin/env python3
"""
Check what's actually in the normalized table for Hidalgo
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("NORMALIZED TABLE CHECK")
print("=" * 80)

# Check if precinct 151 variants exist
print("\n1. Looking for precinct '151' variants in normalized table")
print("-" * 80)

for variant in ['151', '0151']:
    cursor.execute("""
        SELECT original_precinct, normalized_precinct, congressional_district
        FROM precinct_normalized
        WHERE county = 'Hidalgo'
        AND normalized_precinct = ?
        LIMIT 5
    """, (variant,))
    
    results = cursor.fetchall()
    print(f"\nVariant '{variant}': {len(results)} matches")
    for r in results:
        print(f"  Original: '{r['original_precinct']}' → Normalized: '{r['normalized_precinct']}' → District: {r['congressional_district']}")

# Check what's actually in the table for Hidalgo
print("\n2. Sample of Hidalgo precincts in normalized table")
print("-" * 80)

cursor.execute("""
    SELECT DISTINCT original_precinct, normalized_precinct, congressional_district
    FROM precinct_normalized
    WHERE county = 'Hidalgo'
    AND congressional_district = '15'
    ORDER BY original_precinct
    LIMIT 20
""")

print(f"{'Original':<15} {'Normalized':<15} {'District':>10}")
print("-" * 42)
for row in cursor.fetchall():
    print(f"{row['original_precinct']:<15} {row['normalized_precinct']:<15} {row['congressional_district']:>10}")

# Check total count
cursor.execute("""
    SELECT COUNT(*)
    FROM precinct_normalized
    WHERE county = 'Hidalgo'
""")

total = cursor.fetchone()[0]
print(f"\nTotal Hidalgo entries in normalized table: {total:,}")

conn.close()
