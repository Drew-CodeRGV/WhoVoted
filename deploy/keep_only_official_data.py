#!/usr/bin/env python3
"""
Keep ONLY official TX SOS data (tx-sos-evr and tx-sos-election-day)
Delete all other sources (NULL, county-upload) to match official counts
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH, timeout=60.0)
cursor = conn.cursor()

print("="*80)
print("KEEPING ONLY OFFICIAL TX SOS DATA")
print("="*80)

# Check current state
print("\n[BEFORE] Current data by source:")
cursor.execute("""
    SELECT 
        COALESCE(data_source, 'NULL') as source,
        COUNT(DISTINCT vuid) as unique_voters,
        COUNT(*) as total_records
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    GROUP BY data_source
    ORDER BY unique_voters DESC
""")

for source, unique, total in cursor.fetchall():
    print(f"  {source:<30} {unique:>10,} voters  {total:>10,} records")

# Delete non-official data
print("\n[DELETING] Removing non-official data sources...")
cursor.execute("""
    DELETE FROM voter_elections
    WHERE election_date = '2026-03-03'
    AND (data_source IS NULL OR data_source NOT IN ('tx-sos-evr', 'tx-sos-election-day'))
""")

deleted = cursor.rowcount
print(f"  Deleted: {deleted:,} records")

conn.commit()

# Check new state
print("\n[AFTER] Remaining data:")
cursor.execute("""
    SELECT 
        party_voted,
        data_source,
        COUNT(DISTINCT vuid) as unique_voters,
        COUNT(*) as total_records
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    AND party_voted IN ('Democratic', 'Republican')
    GROUP BY party_voted, data_source
    ORDER BY party_voted, data_source
""")

for party, source, unique, total in cursor.fetchall():
    print(f"  {party:<12} {source:<25} {unique:>10,} voters  {total:>10,} records")

# Get totals by party
print("\n[TOTALS] Unique voters by party:")
cursor.execute("""
    SELECT 
        party_voted,
        COUNT(DISTINCT vuid) as unique_voters
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    AND party_voted IN ('Democratic', 'Republican')
    GROUP BY party_voted
""")

for party, unique in cursor.fetchall():
    print(f"  {party:<12} {unique:>10,} voters")

# Check D15 specifically
print("\n[D15 CHECK] Democratic voters in TX-15:")
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
""")

d15_count = cursor.fetchone()[0]
print(f"  D15 Democratic voters: {d15_count:,}")
print(f"  Official count: 54,573")
print(f"  Difference: {d15_count - 54573:,}")

if d15_count == 54573:
    print(f"  ✓ EXACT MATCH!")
elif abs(d15_count - 54573) < 100:
    print(f"  ~ Close (within 100)")
else:
    print(f"  ✗ Still off by {abs(d15_count - 54573):,}")

conn.close()

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
