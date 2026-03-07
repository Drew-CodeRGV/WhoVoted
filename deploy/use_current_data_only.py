#!/usr/bin/env python3
"""
USE CURRENT DATA ONLY

We have 2.97M voting records with precinct data from Texas SOS scrapers.
The 62,876 NULL records are old data from before we had good scrapers.

Solution: Mark NULL records as obsolete and use only current data for district assignment.
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("USE CURRENT DATA ONLY - IGNORE OBSOLETE NULL RECORDS")
print("=" * 80)

# Step 1: Identify what we have
print("\n1. Current Data Status")
print("-" * 80)

cursor.execute("""
    SELECT 
        data_source,
        COUNT(*) as total,
        COUNT(CASE WHEN precinct IS NOT NULL AND precinct != '' THEN 1 END) as with_precinct
    FROM voter_elections
    WHERE election_date = ?
    GROUP BY data_source
    ORDER BY total DESC
""", (ELECTION_DATE,))

print(f"{'Data Source':<30} {'Total':>12} {'With Precinct':>15}")
print("-" * 60)

total_good = 0
total_null = 0

for row in cursor.fetchall():
    source = row['data_source'] or 'NULL (obsolete)'
    print(f"{source:<30} {row['total']:>12,} {row['with_precinct']:>15,}")
    
    if row['data_source']:
        total_good += row['total']
    else:
        total_null += row['total']

print("-" * 60)
print(f"{'GOOD DATA (with source)':<30} {total_good:>12,}")
print(f"{'NULL DATA (obsolete)':<30} {total_null:>12,}")

# Step 2: Mark NULL records as obsolete
print("\n2. Marking NULL records as obsolete...")

cursor.execute("""
    UPDATE voter_elections
    SET data_source = 'obsolete-no-precinct'
    WHERE election_date = ?
    AND (data_source IS NULL OR data_source = '')
    AND (precinct IS NULL OR precinct = '')
""", (ELECTION_DATE,))

marked = cursor.rowcount
conn.commit()

print(f"✓ Marked {marked:,} records as obsolete")

# Step 3: Verify we have good data
print("\n3. Verifying Good Data Coverage")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(*) 
    FROM voter_elections
    WHERE election_date = ?
    AND data_source NOT LIKE 'obsolete%'
    AND precinct IS NOT NULL
    AND precinct != ''
""", (ELECTION_DATE,))

good_with_precinct = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) 
    FROM voter_elections
    WHERE election_date = ?
    AND data_source NOT LIKE 'obsolete%'
""", (ELECTION_DATE,))

good_total = cursor.fetchone()[0]

coverage = 100 * good_with_precinct / good_total if good_total > 0 else 0

print(f"Good data (non-obsolete):     {good_total:,}")
print(f"With precinct data:           {good_with_precinct:,}")
print(f"Coverage:                     {coverage:.1f}%")

# Step 4: Check D15 with good data only
print("\n4. D15 Status (Good Data Only)")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county IN ('Hidalgo', 'Brooks', 'Jim Wells', 'Bee', 'San Patricio', 'Refugio')
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.data_source NOT LIKE 'obsolete%'
""", (ELECTION_DATE,))

d15_total = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county IN ('Hidalgo', 'Brooks', 'Jim Wells', 'Bee', 'San Patricio', 'Refugio')
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.data_source NOT LIKE 'obsolete%'
    AND ve.precinct IS NOT NULL
    AND ve.precinct != ''
""", (ELECTION_DATE,))

d15_with_precinct = cursor.fetchone()[0]

official_d15 = 54573

print(f"D15 Democratic voters (good data):  {d15_total:,}")
print(f"With precinct data:                 {d15_with_precinct:,} ({100*d15_with_precinct/d15_total:.1f}%)")
print(f"Official count:                     {official_d15:,}")
print(f"Difference:                         {d15_total - official_d15:+,}")

print("\n" + "=" * 80)
print("READY FOR DISTRICT ASSIGNMENT")
print("=" * 80)
print("\nNext step: Run build_normalized_precinct_system.py")
print("It will use only the good data (2.97M records with precinct data)")
print("and ignore the obsolete NULL records.")

conn.close()
