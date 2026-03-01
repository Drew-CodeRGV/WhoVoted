#!/usr/bin/env python3
"""Quick DB status check."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db', timeout=5)
conn.execute('PRAGMA journal_mode=WAL')

try:
    r = conn.execute('SELECT COUNT(*) FROM voter_elections WHERE data_source = "tx-sos-evr"').fetchone()
    print(f'EVR records: {r[0]:,}')
    r = conn.execute('SELECT COUNT(*) FROM voters').fetchone()
    print(f'Total voters: {r[0]:,}')
    r = conn.execute('SELECT COUNT(*) FROM voter_elections').fetchone()
    print(f'Total voter_elections: {r[0]:,}')
    r = conn.execute('SELECT COUNT(DISTINCT election_date) FROM voter_elections WHERE data_source = "tx-sos-evr"').fetchone()
    print(f'EVR distinct dates: {r[0]}')
    rows = conn.execute('SELECT election_date, party_voted, COUNT(*) as cnt FROM voter_elections WHERE data_source = "tx-sos-evr" GROUP BY election_date, party_voted ORDER BY election_date, party_voted').fetchall()
    for row in rows:
        print(f'  {row[0]} {row[1]}: {row[2]:,}')
except Exception as e:
    print(f'Error: {e}')

conn.close()
