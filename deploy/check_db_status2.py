#!/usr/bin/env python3
"""Detailed DB status check."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db', timeout=30)
conn.execute('PRAGMA journal_mode=WAL')

print("=== voter_elections by data_source ===")
rows = conn.execute('''
    SELECT data_source, COUNT(*) as cnt 
    FROM voter_elections 
    GROUP BY data_source 
    ORDER BY cnt DESC
''').fetchall()
for row in rows:
    print(f'  {row[0] or "(null)"}: {row[1]:,}')

print("\n=== EVR records by vote_date and party ===")
rows = conn.execute('''
    SELECT vote_date, party_voted, COUNT(*) as cnt 
    FROM voter_elections 
    WHERE data_source = "tx-sos-evr" 
    GROUP BY vote_date, party_voted 
    ORDER BY vote_date, party_voted
''').fetchall()
for row in rows:
    print(f'  {row[0] or "(no date)"} {row[1]}: {row[2]:,}')

print("\n=== election_summary table ===")
try:
    rows = conn.execute('SELECT * FROM election_summary LIMIT 10').fetchall()
    print(f'  {len(rows)} rows')
except Exception as e:
    print(f'  Error: {e}')

print("\n=== Total counts ===")
r = conn.execute('SELECT COUNT(*) FROM voters').fetchone()
print(f'  voters: {r[0]:,}')
r = conn.execute('SELECT COUNT(*) FROM voter_elections').fetchone()
print(f'  voter_elections: {r[0]:,}')

conn.close()
