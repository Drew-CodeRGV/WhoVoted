#!/usr/bin/env python3
"""
Reconcile statewide and county data:
1. Keep all statewide data (tx-sos-evr, tx-sos-election-day) - authoritative
2. Keep county data ONLY for voters not in statewide data
3. Remove duplicate/conflicting records
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH, timeout=60.0)
cursor = conn.cursor()

print("="*80)
print("RECONCILING STATEWIDE AND COUNTY DATA")
print("="*80)

# Step 1: Check current state
print("\n[1] Current data by source:")
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

# Step 2: Find voters in BOTH statewide AND county data
print("\n[2] Finding voters in multiple data sources...")
cursor.execute("""
    SELECT COUNT(DISTINCT vuid)
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    AND vuid IN (
        SELECT vuid FROM voter_elections
        WHERE election_date = '2026-03-03'
        AND data_source IN ('tx-sos-evr', 'tx-sos-election-day')
    )
    AND (data_source IS NULL OR data_source = 'county-upload')
""")

overlap_count = cursor.fetchone()[0]
print(f"  Voters in BOTH statewide AND county data: {overlap_count:,}")

# Step 3: Delete county data for voters who are in statewide data
print("\n[3] Removing county data for voters already in statewide data...")
cursor.execute("""
    DELETE FROM voter_elections
    WHERE election_date = '2026-03-03'
    AND (data_source IS NULL OR data_source = 'county-upload')
    AND vuid IN (
        SELECT DISTINCT vuid FROM voter_elections
        WHERE election_date = '2026-03-03'
        AND data_source IN ('tx-sos-evr', 'tx-sos-election-day')
    )
""")

deleted = cursor.rowcount
print(f"  Deleted {deleted:,} duplicate county records")

conn.commit()

# Step 4: Check final state
print("\n[4] Final data by source:")
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

# Step 5: Total unique voters
print("\n[5] Total unique voters:")
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

# Step 6: Check D15 as bellwether
print("\n[6] D15 Democratic voters (bellwether check):")
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
elif abs(d15_count - 54573) <= 10:
    print(f"  ~ Very close (within 10)")
elif abs(d15_count - 54573) <= 100:
    print(f"  ~ Close (within 100)")
else:
    print(f"  ⚠ Still off by {abs(d15_count - 54573):,}")
    print(f"\n  D15 voters by county:")
    cursor.execute("""
        SELECT 
            v.county,
            COUNT(DISTINCT ve.vuid) as voters
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.congressional_district = '15'
        AND ve.election_date = '2026-03-03'
        AND ve.party_voted = 'Democratic'
        GROUP BY v.county
        ORDER BY voters DESC
        LIMIT 15
    """)
    for county, voters in cursor.fetchall():
        print(f"    {county:<20} {voters:>8,}")

conn.close()

print("\n" + "="*80)
print("RECONCILIATION COMPLETE")
print("="*80)
