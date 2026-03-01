#!/usr/bin/env python3
"""Check upload/processing status in detail."""
import json, os, subprocess

# Check processing jobs
jobs_file = '/opt/whovoted/data/processing_jobs.json'
print("=== Processing Jobs ===")
if os.path.exists(jobs_file):
    with open(jobs_file) as f:
        raw = f.read()
    print(f"Raw content ({len(raw)} bytes):")
    print(raw[:2000])
else:
    print("No jobs file")

# Check if any python geocoding processes are running
print("\n=== Running Python Processes ===")
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
for line in result.stdout.split('\n'):
    if 'python' in line.lower() and 'ps aux' not in line:
        print(f"  {line.strip()}")

# Check gunicorn workers
print("\n=== Gunicorn Workers ===")
for line in result.stdout.split('\n'):
    if 'gunicorn' in line.lower():
        print(f"  {line.strip()}")

# Check supervisor status
print("\n=== Supervisor Status ===")
result2 = subprocess.run(['sudo', 'supervisorctl', 'status'], capture_output=True, text=True)
print(result2.stdout)

# Check recent geocoding stats
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
r = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo' AND geocoded=1").fetchone()
print(f"\n=== DB Stats ===")
print(f"Geocoded voters: {r[0]:,}")
r2 = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo' AND (geocoded=0 OR geocoded IS NULL)").fetchone()
print(f"Not geocoded: {r2[0]:,}")
r3 = conn.execute("SELECT COUNT(*) FROM geocoding_cache").fetchone()
print(f"Cache entries: {r3[0]:,}")

# Check most recent voter_elections entries
print("\n=== Most Recent voter_elections ===")
rows = conn.execute("SELECT created_at, COUNT(*) as cnt FROM voter_elections GROUP BY created_at ORDER BY created_at DESC LIMIT 5").fetchall()
for row in rows:
    print(f"  {row[0]}: {row[1]:,} records")

conn.close()
