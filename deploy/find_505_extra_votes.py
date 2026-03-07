#!/usr/bin/env python3
"""
Find where the 505 extra D15 votes are coming from
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("="*80)
print("FINDING 505 EXTRA D15 VOTES")
print("="*80)

# Check if voters are being counted multiple times due to voting_method
print("\nChecking if same voter appears in multiple voting methods...")
cursor.execute("""
    SELECT 
        ve.vuid,
        COUNT(DISTINCT ve.voting_method) as method_count,
        GROUP_CONCAT(DISTINCT ve.voting_method) as methods
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.vuid
    HAVING COUNT(DISTINCT ve.voting_method) > 1
    LIMIT 10
""")

multi_method = cursor.fetchall()
if multi_method:
    print(f"Found {len(multi_method)} voters in multiple voting methods!")
    for vuid, count, methods in multi_method[:10]:
        print(f"  {vuid}: {methods}")
else:
    print("No voters found in multiple voting methods")

# Check total records vs unique voters
print("\n" + "-"*80)
print("RECORD COUNT ANALYSIS")
print("-"*80)
cursor.execute("""
    SELECT 
        COUNT(*) as total_records,
        COUNT(DISTINCT ve.vuid) as unique_voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
""")
total_records, unique_voters = cursor.fetchone()
print(f"Total records: {total_records:,}")
print(f"Unique voters: {unique_voters:,}")
print(f"Difference: {total_records - unique_voters:,}")

# Check by voting method and data source
print("\n" + "-"*80)
print("BREAKDOWN BY VOTING METHOD AND DATA SOURCE")
print("-"*80)
cursor.execute("""
    SELECT 
        ve.voting_method,
        COALESCE(ve.data_source, 'NULL') as source,
        COUNT(DISTINCT ve.vuid) as unique_voters,
        COUNT(*) as total_records
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.voting_method, ve.data_source
    ORDER BY ve.voting_method, unique_voters DESC
""")

print(f"{'Method':<15} {'Source':<25} {'Unique':>10} {'Records':>10}")
print("-"*65)
for method, source, unique, records in cursor.fetchall():
    dup_flag = " *DUP*" if records > unique else ""
    print(f"{method:<15} {source:<25} {unique:>10,} {records:>10,}{dup_flag}")

# Find actual duplicate records (same vuid, same voting_method, same election_date)
print("\n" + "-"*80)
print("DUPLICATE RECORDS (same vuid + voting_method + election_date)")
print("-"*80)
cursor.execute("""
    SELECT 
        ve.vuid,
        ve.voting_method,
        COUNT(*) as record_count,
        GROUP_CONCAT(COALESCE(ve.data_source, 'NULL')) as sources
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.vuid, ve.voting_method
    HAVING COUNT(*) > 1
    LIMIT 20
""")

true_dups = cursor.fetchall()
if true_dups:
    print(f"Found {len(true_dups)} true duplicate records!")
    for vuid, method, count, sources in true_dups[:20]:
        print(f"  {vuid} ({method}): {count} records from {sources}")
else:
    print("No true duplicate records found (this should not happen!)")

conn.close()

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
