#!/usr/bin/env python3
import sqlite3
import sys

sys.path.insert(0, '/opt/whovoted')

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cursor = conn.cursor()

# Check election_summary table schema
cursor.execute("PRAGMA table_info(election_summary)")
print('election_summary columns:')
for row in cursor.fetchall():
    print(f'  {row[1]} ({row[2]})')

print('\n' + '='*70 + '\n')

# Check election_summary table
cursor.execute("""
    SELECT county, election_date, voting_method, total_voters
    FROM election_summary
    WHERE election_date = '2026-03-03'
    ORDER BY county, voting_method
""")

print('Election summary for 2026-03-03:')
print('County | Voting Method | Total Voters')
print('-' * 70)

results = cursor.fetchall()
for row in results:
    county_short = row[0][:30] if len(row[0]) > 30 else row[0]
    print(f'{county_short:30} | {row[2]:15} | {row[3]:10}')

print(f'\nTotal records: {len(results)}')

# Check specifically for election-day data
cursor.execute("""
    SELECT county, total_voters
    FROM election_summary
    WHERE election_date = '2026-03-03' AND voting_method = 'election-day'
    ORDER BY county
""")

print('\n\nCounties with election-day data for 2026-03-03:')
print('County | Total Voters')
print('-' * 40)
ed_results = cursor.fetchall()
for row in ed_results:
    print(f'{row[0]:30} | {row[1]:8}')

if len(ed_results) == 0:
    print('(none - this is correct, only Hidalgo should have election-day)')

conn.close()
