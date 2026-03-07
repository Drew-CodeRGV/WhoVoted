#!/usr/bin/env python3
"""
Generate SQL UPDATE statements from statewide CSV to backfill precinct data.

Run this LOCALLY where you have the CSV file, then upload the SQL to the server.

Usage:
  python generate_precinct_updates_from_csv.py STATEWIDE_VOTER_INFO.csv > precinct_updates.sql
"""
import csv
import sys

if len(sys.argv) < 2:
    print("Usage: python generate_precinct_updates_from_csv.py <csv_file>")
    print("\nThis will generate SQL UPDATE statements to backfill precinct data.")
    print("Redirect output to a file: > precinct_updates.sql")
    sys.exit(1)

csv_file = sys.argv[1]

print("-- Precinct backfill SQL generated from", csv_file, file=sys.stderr)
print("-- Run this on the server to update voter_elections.precinct", file=sys.stderr)
print(file=sys.stderr)

# Start transaction
print("BEGIN TRANSACTION;")
print()

count = 0
with open(csv_file, 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    
    for row in reader:
        vuid = row.get('id_voter', '').strip()
        precinct = row.get('tx_precinct_code', '').strip()
        
        if vuid and precinct:
            # Escape single quotes in precinct
            precinct_escaped = precinct.replace("'", "''")
            
            print(f"UPDATE voter_elections SET precinct = '{precinct_escaped}', "
                  f"data_source = COALESCE(NULLIF(data_source, ''), 'backfilled-from-csv') "
                  f"WHERE vuid = '{vuid}' AND election_date = '2026-03-03' "
                  f"AND (precinct IS NULL OR precinct = '');")
            
            count += 1
            
            if count % 10000 == 0:
                print(f"-- Processed {count:,} records...", file=sys.stderr)

print()
print("COMMIT;")
print(f"-- Total: {count:,} UPDATE statements generated", file=sys.stderr)
