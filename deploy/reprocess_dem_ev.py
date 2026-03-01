#!/usr/bin/env python3
"""Reprocess the latest DEM EV roster through the EV pipeline."""
import sys
import os
sys.path.insert(0, '/opt/whovoted/backend')

from processor import ProcessingJob
from config import Config

csv_path = '/opt/whovoted/uploads/d6cdd20a-2eca-47df-a6be-df3c8e0be472_EV_DEM_Roster_March_3_2026_Cumulative_202602250654232301.xlsx'

if not os.path.exists(csv_path):
    print(f"ERROR: File not found: {csv_path}")
    sys.exit(1)

print(f"File: {csv_path} ({os.path.getsize(csv_path):,} bytes)")

job = ProcessingJob(
    csv_path,
    year='2026',
    county='Hidalgo',
    election_type='primary',
    election_date='2026-03-03',
    voting_method='early-voting',
    original_filename='EV DEM Roster March 3, 2026 (Cumulative)_202602250654232301.xlsx',
    primary_party='democratic',
    max_workers=20
)

print(f"Job {job.job_id[:8]} created, running...")

try:
    job.run()
    print(f"\nCompleted in {(job.completed_at - job.started_at).total_seconds():.1f}s")
    print(f"  Total: {job.total_records}")
    print(f"  Geocoded: {job.geocoded_count}")
    print(f"  Failed: {job.failed_count}")
except Exception as e:
    print(f"\nFailed: {e}")
    import traceback
    traceback.print_exc()
