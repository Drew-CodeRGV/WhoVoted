#!/usr/bin/env python3
"""Re-process the stuck REP EV roster job."""
import sys
import os
import json

# Add backend to path
sys.path.insert(0, '/opt/whovoted/backend')

from processor import ProcessingJob
from config import Config

# The uploaded file
csv_path = '/opt/whovoted/uploads/afb18983-2734-4fb1-9d6e-6f56e9199142_EV_REP_Roster_March_3_2026_Cumulative_202602250654093913.xlsx'

if not os.path.exists(csv_path):
    print(f"ERROR: File not found: {csv_path}")
    sys.exit(1)

print(f"File found: {csv_path} ({os.path.getsize(csv_path)} bytes)")

# Remove the stuck queued job from disk
jobs_file = Config.DATA_DIR / 'processing_jobs.json'
with open(jobs_file) as f:
    jobs = json.load(f)

old_job_id = '2b0f64af-d43b-4a71-bbf8-19cb1662e188'
if old_job_id in jobs:
    del jobs[old_job_id]
    print(f"Removed stuck job {old_job_id[:8]} from disk")

with open(jobs_file, 'w') as f:
    json.dump(jobs, f, indent=2)

# Create and run a new job
job = ProcessingJob(
    csv_path,
    year='2026',
    county='Hidalgo',
    election_type='primary',
    election_date='2026-03-03',
    voting_method='early-voting',
    original_filename='EV REP Roster March 3, 2026 (Cumulative)_202602250654093913.xlsx',
    primary_party='republican',
    max_workers=20
)

print(f"Created job {job.job_id[:8]}")
print(f"Running...")

# Save initial state to disk
job_data = {
    'job_id': job.job_id,
    'status': 'running',
    'progress': 0.0,
    'total_records': 0,
    'processed_records': 0,
    'geocoded_count': 0,
    'failed_count': 0,
    'cache_hits': 0,
    'county': 'Hidalgo',
    'year': '2026',
    'election_type': 'primary',
    'voting_method': 'early-voting',
    'primary_party': 'republican',
    'original_filename': job.original_filename,
    'started_at': None,
    'completed_at': None,
    'errors': [],
    'log_messages': []
}

with open(jobs_file) as f:
    jobs = json.load(f)
jobs[job.job_id] = job_data
with open(jobs_file, 'w') as f:
    json.dump(jobs, f, indent=2)

try:
    job.run()
    print(f"\nJob completed successfully!")
    print(f"  Total: {job.total_records}")
    print(f"  Geocoded: {job.geocoded_count}")
    print(f"  Failed: {job.failed_count}")
    
    # Update disk state
    with open(jobs_file) as f:
        jobs = json.load(f)
    jobs[job.job_id] = {
        'job_id': job.job_id,
        'status': job.status,
        'progress': job.progress,
        'total_records': job.total_records,
        'processed_records': job.processed_records,
        'geocoded_count': job.geocoded_count,
        'failed_count': job.failed_count,
        'cache_hits': getattr(job, 'cache_hits', 0),
        'county': job.county,
        'year': job.year,
        'election_type': job.election_type,
        'voting_method': job.voting_method,
        'primary_party': getattr(job, 'primary_party', ''),
        'original_filename': job.original_filename,
        'started_at': job.started_at.isoformat() if job.started_at else None,
        'completed_at': job.completed_at.isoformat() if job.completed_at else None,
        'errors': job.errors[:5],
        'log_messages': []
    }
    with open(jobs_file, 'w') as f:
        json.dump(jobs, f, indent=2)
    
except Exception as e:
    print(f"\nJob failed: {e}")
    import traceback
    traceback.print_exc()
