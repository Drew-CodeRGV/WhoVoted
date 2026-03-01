#!/usr/bin/env python3
"""Check voter registry stats for geocoding planning."""
import sqlite3

DB = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

# Total voters
r = conn.execute("""
    SELECT COUNT(*) as total, 
           SUM(CASE WHEN geocoded=1 THEN 1 ELSE 0 END) as geocoded, 
           SUM(CASE WHEN geocoded=0 OR geocoded IS NULL THEN 1 ELSE 0 END) as not_geocoded 
    FROM voters WHERE county='Hidalgo'
""").fetchone()
print(f"Total Hidalgo voters: {r['total']:,}")
print(f"Geocoded: {r['geocoded']:,}")
print(f"Not geocoded: {r['not_geocoded']:,}")

# Not geocoded with addresses
r2 = conn.execute("""
    SELECT COUNT(*) as cnt FROM voters 
    WHERE county='Hidalgo' AND (geocoded=0 OR geocoded IS NULL) 
    AND address IS NOT NULL AND address != ''
""").fetchone()
print(f"Not geocoded with addresses: {r2['cnt']:,}")

# Cache coverage
r3 = conn.execute("SELECT COUNT(*) as cnt FROM geocoding_cache").fetchone()
print(f"Geocoding cache entries: {r3['cnt']:,}")

# Election participation
print("\nElection participation:")
rows = conn.execute("""
    SELECT election_date, party_voted, COUNT(DISTINCT vuid) as cnt 
    FROM voter_elections 
    GROUP BY election_date, party_voted 
    ORDER BY election_date, party_voted
""").fetchall()
for row in rows:
    print(f"  {row['election_date']} {row['party_voted']}: {row['cnt']:,}")

# Party history coverage - how many voters have at least one election record
r4 = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid) as cnt
    FROM voter_elections ve
    INNER JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county='Hidalgo' AND ve.party_voted IS NOT NULL AND ve.party_voted != ''
""").fetchone()
print(f"\nVoters with party history: {r4['cnt']:,}")

# Current party distribution
print("\nCurrent party distribution (from current_party column):")
rows = conn.execute("""
    SELECT current_party, COUNT(*) as cnt 
    FROM voters WHERE county='Hidalgo' 
    GROUP BY current_party ORDER BY cnt DESC
""").fetchall()
for row in rows:
    print(f"  {row['current_party'] or '(null)'}: {row['cnt']:,}")

# Check what the most recent election is
r5 = conn.execute("SELECT MAX(election_date) as latest FROM voter_elections").fetchone()
print(f"\nMost recent election date: {r5['latest']}")

# Check active processing jobs
import json, os
jobs_file = '/opt/whovoted/data/processing_jobs.json'
if os.path.exists(jobs_file):
    with open(jobs_file) as f:
        jobs = json.load(f)
    active = [j for j in jobs if j.get('status') in ('running', 'queued')]
    print(f"\nActive processing jobs: {len(active)}")
    for j in active:
        print(f"  {j.get('filename', '?')} - {j.get('status')} - {j.get('processed', 0)}/{j.get('total', 0)}")

conn.close()
