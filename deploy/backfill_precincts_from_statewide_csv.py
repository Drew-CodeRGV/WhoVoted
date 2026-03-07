#!/usr/bin/env python3
"""
BACKFILL PRECINCTS FROM STATEWIDE CSV

Read the statewide voter info CSV and update voter_elections.precinct
for all records that are missing precinct data.

The CSV has columns:
- id_voter (VUID)
- tx_precinct_code (precinct)
- tx_county_name (county)
- voting_method
"""
import sqlite3
import csv
import os
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

# Look for statewide CSV files
DATA_DIR = Path('/opt/whovoted/data')
POSSIBLE_CSV_NAMES = [
    'STATEWIDE_VOTER_INFO.csv',
    'statewide_voter_info.csv',
    'voter_info.csv',
    'evr_statewide.csv',
    'election_day_statewide.csv'
]

def find_statewide_csv():
    """Find the statewide CSV file."""
    for csv_name in POSSIBLE_CSV_NAMES:
        csv_path = DATA_DIR / csv_name
        if csv_path.exists():
            return csv_path
    
    # Search in subdirectories
    for csv_file in DATA_DIR.rglob('*.csv'):
        if 'statewide' in csv_file.name.lower() or 'voter_info' in csv_file.name.lower():
            return csv_file
    
    return None

print("=" * 80)
print("BACKFILL PRECINCTS FROM STATEWIDE CSV")
print("=" * 80)

# Find CSV file
print("\n1. Looking for statewide CSV file...")
csv_path = find_statewide_csv()

if not csv_path:
    print("   ✗ Could not find statewide CSV file")
    print("\n   Please provide the path to the statewide voter CSV file.")
    print("   Expected columns: id_voter, tx_precinct_code, tx_county_name, voting_method")
    print("\n   Or upload it to: /opt/whovoted/data/STATEWIDE_VOTER_INFO.csv")
    exit(1)

print(f"   ✓ Found: {csv_path}")
print(f"   Size: {csv_path.stat().st_size / 1024 / 1024:.1f} MB")

# Connect to database
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Count records needing update
cursor.execute("""
    SELECT COUNT(*) 
    FROM voter_elections 
    WHERE election_date = ?
    AND (precinct IS NULL OR precinct = '')
""", (ELECTION_DATE,))

needs_update = cursor.fetchone()[0]
print(f"\n2. Records needing precinct data: {needs_update:,}")

if needs_update == 0:
    print("   ✓ All records already have precinct data!")
    conn.close()
    exit(0)

# Parse CSV and build VUID -> precinct mapping
print(f"\n3. Parsing CSV file...")
vuid_precinct_map = {}
line_count = 0

try:
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        # Check for required columns
        if 'id_voter' not in reader.fieldnames:
            print(f"   ✗ CSV missing 'id_voter' column")
            print(f"   Available columns: {', '.join(reader.fieldnames)}")
            exit(1)
        
        if 'tx_precinct_code' not in reader.fieldnames:
            print(f"   ✗ CSV missing 'tx_precinct_code' column")
            print(f"   Available columns: {', '.join(reader.fieldnames)}")
            exit(1)
        
        for row in reader:
            line_count += 1
            vuid = row.get('id_voter', '').strip()
            precinct = row.get('tx_precinct_code', '').strip()
            
            if vuid and precinct:
                vuid_precinct_map[vuid] = precinct
            
            if line_count % 100000 == 0:
                print(f"      Processed {line_count:,} lines, found {len(vuid_precinct_map):,} VUIDs with precincts...")
    
    print(f"   ✓ Parsed {line_count:,} lines")
    print(f"   ✓ Found {len(vuid_precinct_map):,} VUIDs with precinct data")

except Exception as e:
    print(f"   ✗ Error parsing CSV: {e}")
    conn.close()
    exit(1)

# Update database
print(f"\n4. Updating voter_elections table...")
updated = 0
not_found = 0
batch_size = 10000

# Get all records needing update
cursor.execute("""
    SELECT id, vuid
    FROM voter_elections
    WHERE election_date = ?
    AND (precinct IS NULL OR precinct = '')
""", (ELECTION_DATE,))

records_to_update = cursor.fetchall()
total_to_update = len(records_to_update)

print(f"   Processing {total_to_update:,} records...")

for i, record in enumerate(records_to_update):
    record_id = record['id']
    vuid = record['vuid']
    
    if vuid in vuid_precinct_map:
        precinct = vuid_precinct_map[vuid]
        cursor.execute("""
            UPDATE voter_elections
            SET precinct = ?,
                data_source = CASE 
                    WHEN data_source IS NULL OR data_source = '' 
                    THEN 'backfilled-from-csv'
                    ELSE data_source
                END
            WHERE id = ?
        """, (precinct, record_id))
        updated += 1
    else:
        not_found += 1
    
    if (i + 1) % batch_size == 0:
        conn.commit()
        print(f"      Updated {i + 1:,} / {total_to_update:,} records...")

conn.commit()

print(f"\n   ✓ Updated {updated:,} records with precinct data")
print(f"   ✗ Could not find {not_found:,} VUIDs in CSV")

# Verify improvement
print(f"\n5. Verification...")

cursor.execute("""
    SELECT COUNT(*) 
    FROM voter_elections 
    WHERE election_date = ?
    AND (precinct IS NULL OR precinct = '')
""", (ELECTION_DATE,))

remaining = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) 
    FROM voter_elections 
    WHERE election_date = ?
    AND precinct IS NOT NULL
    AND precinct != ''
""", (ELECTION_DATE,))

with_precinct = cursor.fetchone()[0]

cursor.execute("""
    SELECT COUNT(*) 
    FROM voter_elections 
    WHERE election_date = ?
""", (ELECTION_DATE,))

total = cursor.fetchone()[0]

print(f"   Total records: {total:,}")
print(f"   With precinct: {with_precinct:,} ({100*with_precinct/total:.1f}%)")
print(f"   Without precinct: {remaining:,} ({100*remaining/total:.1f}%)")

# Hidalgo specific
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

print("\n" + "=" * 80)
print("NEXT STEP: Run build_normalized_precinct_system.py to assign districts")
print("=" * 80)

conn.close()
