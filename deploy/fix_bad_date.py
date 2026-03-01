#!/usr/bin/env python3
"""Delete the bad 2026-02-27 election records from the database."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Count before
before = conn.execute("SELECT COUNT(*) as cnt FROM voter_elections WHERE election_date = '2026-02-27'").fetchone()['cnt']
print(f"Records with election_date = '2026-02-27': {before}")

if before == 0:
    print("Nothing to delete.")
    conn.close()
    exit(0)

# Show what we're deleting
print("\nBreakdown:")
rows = conn.execute('''
    SELECT ve.election_date, ve.election_type, ve.voting_method, ve.party_voted,
           ve.source_file, COUNT(*) as cnt
    FROM voter_elections ve
    WHERE ve.election_date = '2026-02-27'
    GROUP BY ve.election_date, ve.election_type, ve.voting_method, ve.party_voted, ve.source_file
''').fetchall()
for r in rows:
    print(f"  {r['election_date']} {r['election_type']} {r['voting_method']} {r['party_voted']} source={r['source_file']} count={r['cnt']}")

# Delete
print(f"\nDeleting {before} records...")
conn.execute("DELETE FROM voter_elections WHERE election_date = '2026-02-27'")
conn.commit()

# Verify
after = conn.execute("SELECT COUNT(*) as cnt FROM voter_elections WHERE election_date = '2026-02-27'").fetchone()['cnt']
print(f"Records remaining with 2026-02-27: {after}")

# Show remaining elections
print("\nRemaining elections:")
rows2 = conn.execute('''
    SELECT ve.election_date, ve.election_type, ve.voting_method, ve.party_voted, COUNT(*) as cnt
    FROM voter_elections ve
    GROUP BY ve.election_date, ve.election_type, ve.voting_method, ve.party_voted
    ORDER BY ve.election_date DESC
''').fetchall()
for r in rows2:
    print(f"  {r['election_date']} {r['election_type']} {r['voting_method']} {r['party_voted']} = {r['cnt']}")

total = conn.execute("SELECT COUNT(*) as cnt FROM voter_elections").fetchone()['cnt']
print(f"\nTotal voter_elections records: {total}")

conn.close()
print("\nDone.")
