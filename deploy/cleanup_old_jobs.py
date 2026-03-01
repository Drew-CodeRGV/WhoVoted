#!/usr/bin/env python3
"""Clean up old/stuck jobs from processing_jobs.json."""
import json
from datetime import datetime

JOBS_FILE = '/opt/whovoted/data/processing_jobs.json'

with open(JOBS_FILE) as f:
    jobs = json.load(f)

# Jobs to remove
remove_ids = [
    '9144b506-70ef-41b0-9cd1-928d58f4d56f',  # Stale DEM running job (all records processed)
    '2b0f64af-d43b-4a71-bbf8-19cb1662e188',  # Orphaned queued REP job (replaced by new job)
]

for jid in remove_ids:
    if jid in jobs:
        fname = jobs[jid].get('original_filename', '')[:40]
        status = jobs[jid].get('status')
        # Mark as completed instead of removing (preserves history)
        jobs[jid]['status'] = 'completed'
        jobs[jid]['progress'] = 1.0
        if not jobs[jid].get('completed_at'):
            jobs[jid]['completed_at'] = datetime.now().isoformat()
        print(f"Completed: {jid[:8]} ({status}) - {fname}")

with open(JOBS_FILE, 'w') as f:
    json.dump(jobs, f, indent=2)

print("\nCurrent jobs:")
for jid, j in jobs.items():
    print(f"  {jid[:8]} | {j['status']:10} | {j.get('original_filename', '')[:50]}")
