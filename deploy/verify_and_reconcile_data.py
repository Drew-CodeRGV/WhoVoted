#!/usr/bin/env python3
"""
Verify county data against statewide data and fill gaps:
1. Keep ALL data (statewide + county)
2. Add 'county_verified' flag to mark records that match between sources
3. Identify gaps where county has data but statewide doesn't
4. Report on data quality and completeness
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH, timeout=60.0)
cursor = conn.cursor()

print("="*80)
print("VERIFYING AND RECONCILING DATA")
print("="*80)

# Step 1: Add county_verified column if it doesn't exist
print("\n[1] Adding county_verified tracking column...")
try:
    cursor.execute("ALTER TABLE voter_elections ADD COLUMN county_verified INTEGER DEFAULT 0")
    conn.commit()
    print("  ✓ Added county_verified column")
except sqlite3.OperationalError as e:
    if 'duplicate column' in str(e).lower():
        print("  ✓ Column already exists")
    else:
        raise

# Step 2: Mark county records that are verified by statewide data
print("\n[2] Marking county-verified records...")
cursor.execute("""
    UPDATE voter_elections
    SET county_verified = 1
    WHERE election_date = '2026-03-03'
    AND (data_source IS NULL OR data_source = 'county-upload')
    AND vuid IN (
        SELECT DISTINCT vuid 
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        AND data_source IN ('tx-sos-evr', 'tx-sos-election-day')
    )
""")

verified = cursor.rowcount
print(f"  ✓ Marked {verified:,} county records as verified by statewide data")

conn.commit()

# Step 3: Find gaps - voters in county data but NOT in statewide
print("\n[3] Finding gaps (county data without statewide confirmation)...")
cursor.execute("""
    SELECT COUNT(DISTINCT vuid)
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    AND (data_source IS NULL OR data_source = 'county-upload')
    AND county_verified = 0
""")

gap_voters = cursor.fetchone()[0]
print(f"  Found {gap_voters:,} voters in county data but not yet in statewide data")

if gap_voters > 0:
    print("\n  Breakdown by county:")
    cursor.execute("""
        SELECT 
            v.county,
            COUNT(DISTINCT ve.vuid) as voters
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND (ve.data_source IS NULL OR ve.data_source = 'county-upload')
        AND ve.county_verified = 0
        GROUP BY v.county
        ORDER BY voters DESC
        LIMIT 10
    """)
    for county, voters in cursor.fetchall():
        print(f"    {county:<20} {voters:>8,} voters")

# Step 4: Data quality report
print("\n[4] Data Quality Report:")
cursor.execute("""
    SELECT 
        CASE 
            WHEN data_source IN ('tx-sos-evr', 'tx-sos-election-day') THEN 'Statewide (authoritative)'
            WHEN county_verified = 1 THEN 'County (verified by state)'
            ELSE 'County (not yet in state data)'
        END as status,
        COUNT(DISTINCT vuid) as unique_voters,
        COUNT(*) as total_records
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    GROUP BY status
    ORDER BY unique_voters DESC
""")

print(f"\n  {'Status':<35} {'Voters':>12} {'Records':>12}")
print("  " + "-"*62)
for status, voters, records in cursor.fetchall():
    print(f"  {status:<35} {voters:>12,} {records:>12,}")

# Step 5: Total coverage
print("\n[5] Total Coverage:")
cursor.execute("""
    SELECT 
        party_voted,
        COUNT(DISTINCT vuid) as unique_voters
    FROM voter_elections
    WHERE election_date = '2026-03-03'
    AND party_voted IN ('Democratic', 'Republican')
    GROUP BY party_voted
""")

for party, voters in cursor.fetchall():
    print(f"  {party:<12} {voters:>10,} unique voters")

# Step 6: D15 bellwether check
print("\n[6] D15 Bellwether Check:")
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
""")

d15_total = cursor.fetchone()[0]

# D15 from statewide only
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    AND ve.data_source IN ('tx-sos-evr', 'tx-sos-election-day')
""")

d15_statewide = cursor.fetchone()[0]

# D15 from county only (not verified)
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    AND (ve.data_source IS NULL OR ve.data_source = 'county-upload')
    AND ve.county_verified = 0
""")

d15_county_only = cursor.fetchone()[0]

print(f"  Total D15 Dem voters: {d15_total:,}")
print(f"    From statewide data: {d15_statewide:,}")
print(f"    From county only (gaps): {d15_county_only:,}")
print(f"  Official count: 54,573")
print(f"  Difference: {d15_total - 54573:,}")

conn.close()

print("\n" + "="*80)
print("VERIFICATION COMPLETE")
print("="*80)
print("\nSummary:")
print("  ✓ All data preserved (statewide + county)")
print("  ✓ County data marked as verified where it matches statewide")
print("  ✓ Gaps identified for future statewide data updates")
print("  ✓ System ready for use with quality tracking")
