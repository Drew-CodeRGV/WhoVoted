#!/usr/bin/env python3
"""
HYBRID APPROACH: Use all data with quality flags

This script:
1. Adds a data_quality column to voter_elections
2. Marks records as 'complete' (from scrapers) or 'partial' (from county uploads)
3. Assigns districts to ALL voters based on precinct (including partial data)
4. Provides complete district coverage while maintaining data quality transparency
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("IMPLEMENTING HYBRID APPROACH")
print("=" * 80)

# Step 1: Add data_quality column if it doesn't exist
print("\n1. Adding data_quality column...")
try:
    cursor.execute("""
        ALTER TABLE voter_elections 
        ADD COLUMN data_quality TEXT DEFAULT 'complete'
    """)
    conn.commit()
    print("✓ Column added")
except sqlite3.OperationalError as e:
    if 'duplicate column' in str(e).lower():
        print("✓ Column already exists")
    else:
        raise

# Step 2: Mark data quality levels
print("\n2. Marking data quality levels...")

# Complete data: from SOS scrapers (has party, method, date)
cursor.execute("""
    UPDATE voter_elections
    SET data_quality = 'complete'
    WHERE election_date = ?
    AND data_source IN ('tx-sos-evr', 'tx-sos-election-day')
""", (ELECTION_DATE,))

complete_count = cursor.rowcount
print(f"✓ Marked {complete_count:,} records as 'complete' (from SOS scrapers)")

# Partial data: from county uploads (has precinct but not party/method/date)
cursor.execute("""
    UPDATE voter_elections
    SET data_quality = 'partial',
        data_source = 'county-upload'
    WHERE election_date = ?
    AND data_source LIKE 'obsolete%'
""", (ELECTION_DATE,))

partial_count = cursor.rowcount
print(f"✓ Marked {partial_count:,} records as 'partial' (from county uploads)")

# County upload records that DO have party info
cursor.execute("""
    UPDATE voter_elections
    SET data_quality = 'complete'
    WHERE election_date = ?
    AND data_source = 'county-upload'
    AND party_voted IS NOT NULL
    AND party_voted != ''
""", (ELECTION_DATE,))

upgraded_count = cursor.rowcount
print(f"✓ Upgraded {upgraded_count:,} county records to 'complete' (have party info)")

conn.commit()

# Step 3: Show current status
print("\n3. Current Data Status")
print("-" * 80)

cursor.execute("""
    SELECT 
        data_quality,
        data_source,
        COUNT(*) as count,
        COUNT(CASE WHEN party_voted = 'Democratic' THEN 1 END) as dem,
        COUNT(CASE WHEN party_voted = 'Republican' THEN 1 END) as rep,
        COUNT(CASE WHEN party_voted IS NULL OR party_voted = '' THEN 1 END) as unknown
    FROM voter_elections
    WHERE election_date = ?
    GROUP BY data_quality, data_source
    ORDER BY data_quality, count DESC
""", (ELECTION_DATE,))

print(f"{'Quality':<12} {'Source':<25} {'Total':>12} {'Dem':>10} {'Rep':>10} {'Unknown':>10}")
print("-" * 82)

for row in cursor.fetchall():
    print(f"{row['data_quality']:<12} {row['data_source']:<25} {row['count']:>12,} {row['dem']:>10,} {row['rep']:>10,} {row['unknown']:>10,}")

# Step 4: Hidalgo status
print("\n4. Hidalgo County Status")
print("-" * 80)

cursor.execute("""
    SELECT 
        data_quality,
        COUNT(DISTINCT ve.vuid) as voters,
        COUNT(CASE WHEN ve.party_voted = 'Democratic' THEN 1 END) as dem
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    GROUP BY data_quality
""", (ELECTION_DATE,))

print(f"{'Quality':<12} {'Voters':>12} {'Democratic':>12}")
print("-" * 38)

total_hidalgo = 0
total_hidalgo_dem = 0

for row in cursor.fetchall():
    print(f"{row['data_quality']:<12} {row['voters']:>12,} {row['dem']:>12,}")
    total_hidalgo += row['voters']
    total_hidalgo_dem += row['dem']

print("-" * 38)
print(f"{'TOTAL':<12} {total_hidalgo:>12,} {total_hidalgo_dem:>12,}")

print("\n" + "=" * 80)
print("READY TO ASSIGN DISTRICTS TO ALL VOTERS")
print("=" * 80)
print("\nNext step: Run build_normalized_precinct_system.py")
print("It will now assign districts to ALL voters (complete + partial)")

conn.close()
