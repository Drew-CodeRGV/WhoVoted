#!/usr/bin/env python3
"""
Diagnose why D15 has 55,078 votes instead of 54,573 (505 extra)
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("="*80)
print("D15 DEMOCRATIC VOTE ANALYSIS")
print("="*80)

# Total D15 Dem votes
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
""")
total = cursor.fetchone()[0]
print(f"\nTotal D15 Democratic voters: {total:,}")
print(f"Expected: 54,573")
print(f"Difference: {total - 54573:,}")

# Check for duplicates by data source
print("\n" + "-"*80)
print("VOTES BY DATA SOURCE")
print("-"*80)
cursor.execute("""
    SELECT 
        ve.data_source,
        ve.voting_method,
        COUNT(DISTINCT ve.vuid) as unique_voters,
        COUNT(*) as total_records
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.data_source, ve.voting_method
    ORDER BY ve.data_source, ve.voting_method
""")

for row in cursor.fetchall():
    source, method, unique, total = row
    dup_flag = " (DUPLICATES!)" if total > unique else ""
    print(f"{source or 'NULL':<25} {method or 'NULL':<15} {unique:>8,} voters  {total:>8,} records{dup_flag}")

# Check for voters with multiple records
print("\n" + "-"*80)
print("VOTERS WITH MULTIPLE RECORDS (same election)")
print("-"*80)
cursor.execute("""
    SELECT 
        ve.vuid,
        v.firstname,
        v.lastname,
        COUNT(*) as record_count,
        GROUP_CONCAT(ve.voting_method || ' (' || COALESCE(ve.data_source, 'NULL') || ')') as methods
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.vuid
    HAVING COUNT(*) > 1
    LIMIT 20
""")

duplicates = cursor.fetchall()
if duplicates:
    print(f"\nFound {len(duplicates)} voters with multiple records (showing first 20):")
    for vuid, first, last, count, methods in duplicates:
        print(f"  {vuid}: {first} {last} - {count} records: {methods}")
else:
    print("\nNo duplicate records found")

# Check total unique voters across all voting methods
print("\n" + "-"*80)
print("UNIQUE VOTERS BY VOTING METHOD")
print("-"*80)
cursor.execute("""
    SELECT 
        ve.voting_method,
        COUNT(DISTINCT ve.vuid) as unique_voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.voting_method
    ORDER BY ve.voting_method
""")

method_totals = {}
for method, count in cursor.fetchall():
    method_totals[method or 'NULL'] = count
    print(f"{method or 'NULL':<20} {count:>8,} voters")

# Check if voters appear in multiple voting methods
print("\n" + "-"*80)
print("VOTERS IN MULTIPLE VOTING METHODS")
print("-"*80)
cursor.execute("""
    SELECT 
        ve.vuid,
        v.firstname,
        v.lastname,
        GROUP_CONCAT(DISTINCT ve.voting_method) as methods,
        COUNT(DISTINCT ve.voting_method) as method_count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.vuid
    HAVING COUNT(DISTINCT ve.voting_method) > 1
    LIMIT 20
""")

multi_method = cursor.fetchall()
if multi_method:
    print(f"\nFound {len(multi_method)} voters in multiple voting methods (showing first 20):")
    for vuid, first, last, methods, count in multi_method:
        print(f"  {vuid}: {first} {last} - {methods}")
else:
    print("\nNo voters found in multiple voting methods")

conn.close()

print("\n" + "="*80)
print("ANALYSIS COMPLETE")
print("="*80)
