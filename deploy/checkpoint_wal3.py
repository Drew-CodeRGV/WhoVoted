#!/usr/bin/env python3
"""Checkpoint WAL file and check DB status."""
import sqlite3
import time

db_path = '/opt/whovoted/data/whovoted.db'

print("Connecting to DB...")
conn = sqlite3.connect(db_path, timeout=60)
conn.execute("PRAGMA journal_mode=WAL")

print("Running WAL checkpoint (TRUNCATE)...")
start = time.time()
result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
elapsed = time.time() - start
print(f"Checkpoint result: {result} ({elapsed:.1f}s)")

print("\nDB status:")
r = conn.execute('SELECT COUNT(*) FROM voters').fetchone()
print(f'  Total voters: {r[0]:,}')
r = conn.execute('SELECT COUNT(*) FROM voter_elections').fetchone()
print(f'  Total voter_elections: {r[0]:,}')
r = conn.execute('SELECT COUNT(*) FROM voter_elections WHERE data_source = "tx-sos-evr"').fetchone()
print(f'  EVR records: {r[0]:,}')

print("\nEVR breakdown by date/party:")
rows = conn.execute('''
    SELECT election_date, party_voted, COUNT(*) as cnt 
    FROM voter_elections 
    WHERE data_source = "tx-sos-evr" 
    GROUP BY election_date, party_voted 
    ORDER BY party_voted, election_date
''').fetchall()
for row in rows:
    print(f'  {row[0]} {row[1]}: {row[2]:,}')

conn.close()
print("\nDone.")
