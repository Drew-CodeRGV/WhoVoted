#!/usr/bin/env python3
"""Full status check - jobs, DB, running processes."""
import json, os, sqlite3, subprocess

DB = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB)

# Check ALL job files
print("=== Processing Jobs (full dump) ===")
jobs_file = '/opt/whovoted/data/processing_jobs.json'
if os.path.exists(jobs_file):
    with open(jobs_file) as f:
        data = json.load(f)
    if isinstance(data, dict):
        for jid, j in data.items():
            if isinstance(j, dict):
                print(f"  Job {jid[:12]}:")
                print(f"    status: {j.get('status')}")
                print(f"    progress: {j.get('progress')}")
                print(f"    processed: {j.get('processed_records', j.get('processed', '?'))}/{j.get('total_records', j.get('total', '?'))}")
                print(f"    geocoded: {j.get('geocoded_count', '?')}")
                print(f"    filename: {j.get('original_filename', j.get('filename', '?'))}")
                print(f"    started: {j.get('started_at', '?')}")
                print(f"    completed: {j.get('completed_at', '?')}")
            else:
                print(f"  {jid}: {j}")
    elif isinstance(data, list):
        for j in data:
            print(f"  {j}")

# Check batch geocode status
print("\n=== Batch Geocode Status ===")
status_file = '/opt/whovoted/data/batch_geocode_status.json'
if os.path.exists(status_file):
    with open(status_file) as f:
        s = json.load(f)
    for k, v in s.items():
        print(f"  {k}: {v}")
else:
    print("  No batch geocode status file found")

# Check geocode_registry status
print("\n=== Geocode Registry Status ===")
reg_status = '/opt/whovoted/data/geocode_registry_status.json'
if os.path.exists(reg_status):
    with open(reg_status) as f:
        s = json.load(f)
    for k, v in s.items():
        print(f"  {k}: {v}")
else:
    print("  No geocode registry status file found")

# DB stats
print("\n=== DB Stats ===")
r = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo'").fetchone()
print(f"  Total voters: {r[0]:,}")
r = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo' AND geocoded=1").fetchone()
print(f"  Geocoded: {r[0]:,}")
r = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo' AND (geocoded=0 OR geocoded IS NULL)").fetchone()
print(f"  Not geocoded: {r[0]:,}")
r = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo' AND geocoded=-1").fetchone()
print(f"  Failed (geocoded=-1): {r[0]:,}")
r = conn.execute("SELECT COUNT(*) FROM geocoding_cache").fetchone()
print(f"  Cache entries: {r[0]:,}")

# Election stats
print("\n=== Election Participation ===")
rows = conn.execute("""
    SELECT election_date, COUNT(DISTINCT vuid) as cnt 
    FROM voter_elections GROUP BY election_date ORDER BY election_date
""").fetchall()
for row in rows:
    print(f"  {row[0]}: {row[1]:,}")

# Check if voter_addresses table exists
print("\n=== voter_addresses table ===")
try:
    r = conn.execute("SELECT COUNT(*) FROM voter_addresses").fetchone()
    print(f"  Entries: {r[0]:,}")
except:
    print("  Table does not exist yet")

# Running python processes
print("\n=== Running Python Processes ===")
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
for line in result.stdout.split('\n'):
    if 'python' in line.lower() and 'ps aux' not in line and 'check_full_status' not in line:
        # Trim to fit
        parts = line.strip().split()
        if len(parts) > 10:
            cmd = ' '.join(parts[10:])
            cpu = parts[2]
            mem = parts[3]
            print(f"  CPU:{cpu}% MEM:{mem}% CMD:{cmd[:80]}")

conn.close()
