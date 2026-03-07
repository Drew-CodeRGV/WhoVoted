#!/usr/bin/env python3
"""
Investigate county upload data - where did it go and why doesn't it have precinct data?
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("INVESTIGATING COUNTY UPLOAD DATA")
print("=" * 80)

# Check data sources
print("\n1. DATA SOURCES BREAKDOWN")
print("-" * 80)

cursor.execute("""
    SELECT 
        data_source,
        COUNT(*) as total_records,
        COUNT(DISTINCT vuid) as unique_voters,
        COUNT(CASE WHEN precinct IS NOT NULL AND precinct != '' THEN 1 END) as with_precinct,
        COUNT(CASE WHEN precinct IS NULL OR precinct = '' THEN 1 END) as without_precinct
    FROM voter_elections
    WHERE election_date = ?
    GROUP BY data_source
    ORDER BY total_records DESC
""", (ELECTION_DATE,))

print(f"{'Data Source':<30} {'Records':>12} {'Unique':>12} {'W/Precinct':>12} {'No Precinct':>12}")
print("-" * 80)

for row in cursor.fetchall():
    source = row['data_source'] or 'NULL'
    print(f"{source:<30} {row['total_records']:>12,} {row['unique_voters']:>12,} {row['with_precinct']:>12,} {row['without_precinct']:>12,}")

# Check Hidalgo specifically
print("\n2. HIDALGO COUNTY - DATA SOURCE BREAKDOWN")
print("-" * 80)

cursor.execute("""
    SELECT 
        ve.data_source,
        COUNT(*) as total_records,
        COUNT(DISTINCT ve.vuid) as unique_voters,
        COUNT(CASE WHEN ve.precinct IS NOT NULL AND ve.precinct != '' THEN 1 END) as with_precinct,
        COUNT(CASE WHEN ve.party_voted = 'Democratic' THEN 1 END) as democratic
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    GROUP BY ve.data_source
    ORDER BY total_records DESC
""", (ELECTION_DATE,))

print(f"{'Data Source':<30} {'Records':>12} {'Unique':>12} {'W/Precinct':>12} {'Democratic':>12}")
print("-" * 80)

for row in cursor.fetchall():
    source = row['data_source'] or 'NULL'
    print(f"{source:<30} {row['total_records']:>12,} {row['unique_voters']:>12,} {row['with_precinct']:>12,} {row['democratic']:>12,}")

# Check source files
print("\n3. HIDALGO COUNTY - SOURCE FILES")
print("-" * 80)

cursor.execute("""
    SELECT 
        ve.source_file,
        ve.data_source,
        COUNT(*) as count,
        COUNT(CASE WHEN ve.precinct IS NOT NULL AND ve.precinct != '' THEN 1 END) as with_precinct,
        COUNT(CASE WHEN ve.party_voted = 'Democratic' THEN 1 END) as democratic
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    GROUP BY ve.source_file, ve.data_source
    ORDER BY count DESC
    LIMIT 20
""", (ELECTION_DATE,))

print(f"{'Source File':<50} {'Data Source':<20} {'Count':>10} {'W/Prec':>10} {'Dem':>10}")
print("-" * 80)

for row in cursor.fetchall():
    source_file = (row['source_file'] or 'NULL')[:48]
    data_source = (row['data_source'] or 'NULL')[:18]
    print(f"{source_file:<50} {data_source:<20} {row['count']:>10,} {row['with_precinct']:>10,} {row['democratic']:>10,}")

# Sample records from each source
print("\n4. SAMPLE RECORDS FROM EACH DATA SOURCE")
print("-" * 80)

for source in ['tx-sos-evr', 'tx-sos-election-day', 'county-upload', None]:
    print(f"\nData Source: {source or 'NULL'}")
    
    cursor.execute("""
        SELECT 
            ve.vuid,
            ve.precinct,
            ve.party_voted,
            ve.voting_method,
            ve.source_file,
            v.county
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
        AND ve.election_date = ?
        AND ve.data_source IS ?
        LIMIT 5
    """, (ELECTION_DATE, source))
    
    for row in cursor.fetchall():
        precinct = row['precinct'] or 'NULL'
        source_file = (row['source_file'] or 'NULL')[:40]
        print(f"  VUID: {row['vuid']}, Precinct: '{precinct}', Party: {row['party_voted']}, File: {source_file}")

# Check if county upload data exists at all
print("\n5. COUNTY UPLOAD DATA - OVERALL")
print("-" * 80)

cursor.execute("""
    SELECT COUNT(*) FROM voter_elections 
    WHERE data_source = 'county-upload'
""")
county_upload_count = cursor.fetchone()[0]

print(f"Total county-upload records: {county_upload_count:,}")

if county_upload_count > 0:
    cursor.execute("""
        SELECT 
            v.county,
            COUNT(*) as count,
            COUNT(CASE WHEN ve.precinct IS NOT NULL AND ve.precinct != '' THEN 1 END) as with_precinct
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.data_source = 'county-upload'
        GROUP BY v.county
        ORDER BY count DESC
    """)
    
    print(f"\n{'County':<20} {'Records':>12} {'With Precinct':>15}")
    print("-" * 50)
    
    for row in cursor.fetchall():
        print(f"{row['county']:<20} {row['count']:>12,} {row['with_precinct']:>15,}")

# Check if the problem is that county data was OVERWRITTEN by scraper data
print("\n6. DUPLICATE DETECTION - Same VUID, Different Sources")
print("-" * 80)

cursor.execute("""
    SELECT 
        ve.vuid,
        GROUP_CONCAT(DISTINCT ve.data_source) as sources,
        COUNT(DISTINCT ve.data_source) as source_count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = ?
    GROUP BY ve.vuid
    HAVING source_count > 1
    LIMIT 10
""", (ELECTION_DATE,))

duplicates = cursor.fetchall()

if duplicates:
    print(f"Found {len(duplicates)} voters with records from multiple sources")
    print("\nSample duplicates:")
    for row in duplicates:
        print(f"  VUID: {row['vuid']}, Sources: {row['sources']}")
else:
    print("No duplicates found - each voter has records from only ONE source")

conn.close()
