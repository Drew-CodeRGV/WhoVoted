#!/usr/bin/env python3
"""
COPY PRECINCT FROM VOTERS TABLE TO VOTER_ELECTIONS

The voters table has precinct data from voter registration files.
The voter_elections table is missing precinct for 49,637 Hidalgo voters.
This script copies the precinct data over.
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("COPY PRECINCT FROM VOTERS TABLE TO VOTER_ELECTIONS")
print("=" * 80)

# Step 1: Check current status
print("\n1. Current Status")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(*)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = ?
    AND (ve.precinct IS NULL OR ve.precinct = '')
    AND v.precinct IS NOT NULL
    AND v.precinct != ''
""", (ELECTION_DATE,))

can_fix = cursor.fetchone()[0]
print(f"Records that can be fixed: {can_fix:,}")

# Step 2: Copy precinct data
print("\n2. Copying precinct data...")

cursor.execute("""
    UPDATE voter_elections
    SET precinct = (
        SELECT v.precinct
        FROM voters v
        WHERE v.vuid = voter_elections.vuid
    )
    WHERE election_date = ?
    AND (precinct IS NULL OR precinct = '')
    AND EXISTS (
        SELECT 1 FROM voters v
        WHERE v.vuid = voter_elections.vuid
        AND v.precinct IS NOT NULL
        AND v.precinct != ''
    )
""", (ELECTION_DATE,))

updated = cursor.rowcount
conn.commit()

print(f"✓ Updated {updated:,} records")

# Step 3: Verify Hidalgo coverage
print("\n3. Hidalgo Coverage After Fix")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
""", (ELECTION_DATE,))

total = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.precinct IS NOT NULL
    AND ve.precinct != ''
""", (ELECTION_DATE,))

with_precinct = cursor.fetchone()[0]

coverage = 100 * with_precinct / total if total > 0 else 0

print(f"Hidalgo Democratic voters:")
print(f"  Total:           {total:>10,}")
print(f"  With precinct:   {with_precinct:>10,} ({coverage:.1f}%)")

# Step 4: Overall coverage
print("\n4. Overall Coverage After Fix")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(*)
    FROM voter_elections
    WHERE election_date = ?
""", (ELECTION_DATE,))

total_all = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*)
    FROM voter_elections
    WHERE election_date = ?
    AND precinct IS NOT NULL
    AND precinct != ''
""", (ELECTION_DATE,))

with_precinct_all = cursor.fetchone()[0]

coverage_all = 100 * with_precinct_all / total_all if total_all > 0 else 0

print(f"All voters:")
print(f"  Total:           {total_all:>10,}")
print(f"  With precinct:   {with_precinct_all:>10,} ({coverage_all:.1f}%)")

print("\n" + "=" * 80)
print("PRECINCT DATA COPIED SUCCESSFULLY")
print("=" * 80)
print("\nNext step: Run build_normalized_precinct_system.py to assign districts")

conn.close()
