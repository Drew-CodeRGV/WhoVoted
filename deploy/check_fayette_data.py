#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cursor = conn.cursor()

# Check election_summary
cursor.execute("""
    SELECT voting_method, party_voted, total_voters, geocoded_count
    FROM election_summary
    WHERE county = 'Fayette' AND election_date = '2026-03-03'
    ORDER BY voting_method, party_voted
""")

print('Election Summary for Fayette County (2026-03-03):')
print('Voting Method | Party | Total | Geocoded')
print('-' * 60)
for row in cursor.fetchall():
    print(f'{row[0]:15} | {row[1]:10} | {row[2]:6} | {row[3]:8}')

# Check if there are actual voter records
cursor.execute("""
    SELECT COUNT(*) 
    FROM voter_elections ve
    JOIN voters v ON ve.voter_id = v.id
    WHERE v.county = 'Fayette' AND ve.election_date = '2026-03-03'
""")

voter_count = cursor.fetchone()[0]
print(f'\nActual voter records in voters table: {voter_count}')

# Check voter_addresses for geocoded data
cursor.execute("""
    SELECT COUNT(DISTINCT va.voter_id)
    FROM voter_addresses va
    JOIN voters v ON va.voter_id = v.id
    JOIN voter_elections ve ON v.id = ve.voter_id
    WHERE v.county = 'Fayette' 
    AND ve.election_date = '2026-03-03'
    AND va.latitude IS NOT NULL 
    AND va.longitude IS NOT NULL
""")

geocoded_count = cursor.fetchone()[0]
print(f'Geocoded voter records: {geocoded_count}')

conn.close()
