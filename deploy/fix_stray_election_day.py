#!/usr/bin/env python3
"""
Fix stray election-day records that should be early-voting.
Only Hidalgo County should have election-day data for 2026-03-03.
All other counties with election-day data are stragglers that should be DELETED.
"""
import sqlite3
import sys

sys.path.insert(0, '/opt/whovoted')

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cursor = conn.cursor()

# Find all election-day records for 2026-03-03 that are NOT Hidalgo
cursor.execute("""
    SELECT county, party_voted, total_voters
    FROM election_summary
    WHERE election_date = '2026-03-03' 
    AND voting_method = 'election-day'
    AND county != 'Hidalgo'
    ORDER BY county, party_voted
""")

stray_records = cursor.fetchall()

if len(stray_records) == 0:
    print('No stray election-day records found. Database is clean!')
    conn.close()
    sys.exit(0)

print(f'Found {len(stray_records)} stray election-day records:')
for county, party, count in stray_records:
    print(f'  {county} ({party}): {count} voters')

print('\nThese are stragglers (1-2 voters) that got mislabeled.')
print('They will be DELETED from election_summary.')
response = input('\nProceed with deletion? (yes/no): ')

if response.lower() != 'yes':
    print('Aborted.')
    conn.close()
    sys.exit(0)

# Delete stray election-day records
cursor.execute("""
    DELETE FROM election_summary
    WHERE election_date = '2026-03-03'
    AND voting_method = 'election-day'
    AND county != 'Hidalgo'
""")

deleted_count = cursor.rowcount
conn.commit()

print(f'\nDeleted {deleted_count} stray election-day records.')
print('Election-day data now only exists for Hidalgo County.')

# Verify
cursor.execute("""
    SELECT county, party_voted, total_voters
    FROM election_summary
    WHERE election_date = '2026-03-03' 
    AND voting_method = 'election-day'
    ORDER BY county, party_voted
""")

remaining = cursor.fetchall()
print('\nRemaining election-day records:')
for county, party, count in remaining:
    print(f'  {county} ({party}): {count} voters')

conn.close()
