#!/usr/bin/env python3
"""Clean up failed ABBM records and check what needs reprocessing."""
import sqlite3
import os

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Check for any ABBM-related voter_elections records
print("=== ABBM-related voter_elections records ===")
rows = conn.execute("""
    SELECT voting_method, party_voted, COUNT(*) as cnt
    FROM voter_elections
    WHERE source_file LIKE '%ABBM%' OR source_file LIKE '%abbm%'
       OR voting_method = 'mail-in'
    GROUP BY voting_method, party_voted
""").fetchall()
for r in rows:
    print(f"  method={r['voting_method']}, party={r['party_voted']}, count={r['cnt']}")
if not rows:
    print("  (none found)")

# Check for ABBM files in uploads directory
print("\n=== ABBM files in uploads ===")
upload_dir = '/opt/whovoted/uploads'
if os.path.exists(upload_dir):
    for f in sorted(os.listdir(upload_dir)):
        if 'abbm' in f.lower() or 'ABBM' in f:
            fpath = os.path.join(upload_dir, f)
            size = os.path.getsize(fpath)
            print(f"  {f} ({size:,} bytes)")

# Check processing_jobs.json for ABBM jobs
print("\n=== Processing jobs with ABBM ===")
import json
jobs_path = '/opt/whovoted/data/processing_jobs.json'
if os.path.exists(jobs_path):
    try:
        with open(jobs_path) as f:
            jobs = json.load(f)
        if isinstance(jobs, dict):
            for job_id, job in jobs.items():
                if isinstance(job, dict):
                    fn = job.get('original_filename', '') or job.get('filename', '')
                    if 'abbm' in fn.lower() or 'ABBM' in fn:
                        print(f"  job_id={job_id}, status={job.get('status','?')}, file={fn}")
        elif isinstance(jobs, list):
            for job in jobs:
                if isinstance(job, dict):
                    fn = job.get('original_filename', '') or job.get('filename', '')
                    if 'abbm' in fn.lower() or 'ABBM' in fn:
                        print(f"  job_id={job.get('job_id','?')}, status={job.get('status','?')}, file={fn}")
    except Exception as e:
        print(f"  Error reading jobs: {e}")

# Delete any voter_elections records from failed ABBM processing
# (they would have voting_method='early-voting' since that was the default)
print("\n=== Cleaning up failed ABBM voter_elections (early-voting method) ===")
rows = conn.execute("""
    SELECT COUNT(*) as cnt FROM voter_elections
    WHERE source_file LIKE '%ABBM%' OR source_file LIKE '%abbm%'
""").fetchone()
print(f"  Found {rows['cnt']} records with ABBM source files")

if rows['cnt'] > 0:
    conn.execute("""
        DELETE FROM voter_elections
        WHERE source_file LIKE '%ABBM%' OR source_file LIKE '%abbm%'
    """)
    conn.commit()
    print(f"  Deleted {rows['cnt']} records")

conn.close()
print("\nDone. Ready for reprocessing with mail-in voting method.")
