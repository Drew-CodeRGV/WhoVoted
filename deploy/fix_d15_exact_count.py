#!/usr/bin/env python3
"""
Fix D15 to have exactly 54,573 Democratic voters by removing duplicates
Strategy: Keep tx-sos-evr and tx-sos-election-day (official sources), remove overlaps from other sources
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("="*80)
print("FIXING D15 DUPLICATE VOTES")
print("="*80)

# Find voters in D15 Dem primary with records from multiple sources
print("\nFinding voters with multiple data sources...")
cursor.execute("""
    SELECT 
        ve.vuid,
        GROUP_CONCAT(DISTINCT COALESCE(ve.data_source, 'NULL')) as sources,
        COUNT(DISTINCT COALESCE(ve.data_source, 'NULL')) as source_count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY ve.vuid
    HAVING COUNT(DISTINCT COALESCE(ve.data_source, 'NULL')) > 1
""")

multi_source_voters = cursor.fetchall()
print(f"Found {len(multi_source_voters)} voters with multiple data sources")

if multi_source_voters:
    print(f"\nSample (first 5):")
    for vuid, sources, count in multi_source_voters[:5]:
        print(f"  {vuid}: {sources}")

# Delete records where:
# - Voter is in D15 Dem primary
# - data_source is NULL or 'county-upload'
# - AND the same voter has a record from 'tx-sos-evr' or 'tx-sos-election-day'
print("\nRemoving duplicate records from less authoritative sources...")
cursor.execute("""
    DELETE FROM voter_elections
    WHERE id IN (
        SELECT ve1.id
        FROM voter_elections ve1
        JOIN voters v ON ve1.vuid = v.vuid
        WHERE v.congressional_district = '15'
        AND ve1.election_date = '2026-03-03'
        AND ve1.party_voted = 'Democratic'
        AND (ve1.data_source IS NULL OR ve1.data_source = 'county-upload')
        AND EXISTS (
            SELECT 1 FROM voter_elections ve2
            WHERE ve2.vuid = ve1.vuid
            AND ve2.election_date = '2026-03-03'
            AND ve2.party_voted = 'Democratic'
            AND ve2.data_source IN ('tx-sos-evr', 'tx-sos-election-day')
        )
    )
""")

deleted = cursor.rowcount
print(f"Deleted {deleted:,} duplicate records")

conn.commit()

# Verify new count
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
""")
new_count = cursor.fetchone()[0]

print("\n" + "-"*80)
print("RESULTS")
print("-"*80)
print(f"D15 Democratic voters: {new_count:,}")
print(f"Official count: 54,573")
print(f"Match: {'✓ YES' if new_count == 54573 else f'✗ NO (off by {new_count - 54573:,})'}")

conn.close()

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
