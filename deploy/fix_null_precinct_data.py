#!/usr/bin/env python3
"""
FIX NULL PRECINCT DATA

The problem: 62,873 Hidalgo voters have data_source=NULL and no precinct data.
These are old records that need to be updated with precinct data from:
1. Statewide CSV files (if available)
2. County upload files
3. Texas SOS scrapers

Strategy:
- For each NULL record, try to find the same VUID in newer data sources
- Copy the precinct data from the newer source
- Mark the data_source appropriately
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("FIXING NULL PRECINCT DATA")
print("=" * 80)

# Step 1: Identify NULL records
print("\n1. Identifying NULL records...")
cursor.execute("""
    SELECT COUNT(*) 
    FROM voter_elections 
    WHERE election_date = ?
    AND (data_source IS NULL OR data_source = '')
    AND (precinct IS NULL OR precinct = '')
""", (ELECTION_DATE,))

null_no_precinct = cursor.fetchone()[0]
print(f"   Found {null_no_precinct:,} NULL records without precinct data")

# Step 2: Check if these VUIDs exist in other data sources WITH precinct
print("\n2. Checking for duplicates in other data sources...")
cursor.execute("""
    SELECT 
        ve_null.id as null_id,
        ve_null.vuid,
        ve_other.precinct as other_precinct,
        ve_other.data_source as other_source,
        ve_other.source_file as other_file
    FROM voter_elections ve_null
    LEFT JOIN voter_elections ve_other ON ve_null.vuid = ve_other.vuid
        AND ve_other.election_date = ve_null.election_date
        AND ve_other.data_source IS NOT NULL
        AND ve_other.data_source != ''
        AND ve_other.precinct IS NOT NULL
        AND ve_other.precinct != ''
    WHERE ve_null.election_date = ?
    AND (ve_null.data_source IS NULL OR ve_null.data_source = '')
    AND (ve_null.precinct IS NULL OR ve_null.precinct = '')
    AND ve_other.id IS NOT NULL
""", (ELECTION_DATE,))

duplicates = cursor.fetchall()
print(f"   Found {len(duplicates):,} NULL records that have duplicates with precinct data")

if len(duplicates) > 0:
    print("\n3. Updating NULL records with precinct data from duplicates...")
    
    updated = 0
    for dup in duplicates:
        cursor.execute("""
            UPDATE voter_elections
            SET precinct = ?,
                data_source = 'backfilled-from-' || ?,
                source_file = ?
            WHERE id = ?
        """, (dup['other_precinct'], dup['other_source'], dup['other_file'], dup['null_id']))
        updated += 1
        
        if updated % 10000 == 0:
            conn.commit()
            print(f"      Updated {updated:,} / {len(duplicates):,} records...")
    
    conn.commit()
    print(f"   ✓ Updated {updated:,} records with precinct data")

# Step 4: Check remaining NULL records
print("\n4. Checking remaining NULL records...")
cursor.execute("""
    SELECT COUNT(*) 
    FROM voter_elections 
    WHERE election_date = ?
    AND (data_source IS NULL OR data_source = '')
    AND (precinct IS NULL OR precinct = '')
""", (ELECTION_DATE,))

remaining = cursor.fetchone()[0]
print(f"   Remaining NULL records without precinct: {remaining:,}")

if remaining > 0:
    print("\n   These records don't have duplicates - they may be:")
    print("   - Voters who only appear in old data")
    print("   - Voters who haven't been re-scraped yet")
    print("   - Data quality issues")
    
    # Show sample
    cursor.execute("""
        SELECT ve.vuid, ve.party_voted, v.county
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ?
        AND (ve.data_source IS NULL OR ve.data_source = '')
        AND (ve.precinct IS NULL OR ve.precinct = '')
        LIMIT 10
    """, (ELECTION_DATE,))
    
    print("\n   Sample remaining NULL records:")
    for row in cursor.fetchall():
        print(f"      VUID: {row['vuid']}, Party: {row['party_voted']}, County: {row['county']}")

# Step 5: Re-run district assignment
print("\n5. Re-running district assignment with updated precinct data...")
print("   (This will be done by build_normalized_precinct_system.py)")

# Step 6: Verify improvement
print("\n6. Verification...")

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

hidalgo_with_precinct = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
""", (ELECTION_DATE,))

hidalgo_total = cursor.fetchone()[0]

print(f"\n   Hidalgo Democratic voters:")
print(f"      Total: {hidalgo_total:,}")
print(f"      With precinct: {hidalgo_with_precinct:,} ({100*hidalgo_with_precinct/hidalgo_total:.1f}%)")
print(f"      Without precinct: {hidalgo_total - hidalgo_with_precinct:,}")

print("\n" + "=" * 80)
print("NEXT STEP: Run build_normalized_precinct_system.py to assign districts")
print("=" * 80)

conn.close()
