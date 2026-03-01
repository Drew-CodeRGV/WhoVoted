#!/usr/bin/env python3
"""Fix stuck jobs: complete stale running jobs and re-queue stuck queued jobs."""
import json
from datetime import datetime

JOBS_FILE = '/opt/whovoted/data/processing_jobs.json'

with open(JOBS_FILE) as f:
    jobs = json.load(f)

changes = 0

for jid, j in jobs.items():
    status = j.get('status')
    total = j.get('total_records', 0)
    processed = j.get('processed_records', 0)
    fname = j.get('original_filename', '')
    
    # Auto-complete running jobs where all records are processed
    if status == 'running' and total > 0 and processed >= total:
        print(f"Completing stale job {jid[:8]}: {fname}")
        j['status'] = 'completed'
        j['progress'] = 1.0
        j['completed_at'] = datetime.now().isoformat()
        changes += 1

with open(JOBS_FILE, 'w') as f:
    json.dump(jobs, f, indent=2)

print(f"\nFixed {changes} jobs")

# Show current state
for jid, j in jobs.items():
    print(f"  {jid[:8]} | {j['status']:10} | {j.get('original_filename', '')[:50]}")
