#!/usr/bin/env python3
"""Check recent processing job status."""
import json
import sys

with open('/opt/whovoted/data/processing_jobs.json') as f:
    jobs = json.load(f)

# Handle both dict and list formats
if isinstance(jobs, dict):
    job_list = list(jobs.values())
else:
    job_list = jobs

for j in job_list[-5:]:
    print(f"Job: {j['job_id'][:8]}")
    print(f"  File: {j.get('original_filename', 'N/A')}")
    print(f"  Status: {j['status']}")
    print(f"  Total: {j.get('total_records', 0)}")
    print(f"  Geocoded: {j.get('geocoded_count', 0)}")
    print(f"  Failed: {j.get('failed_count', 0)}")
    print(f"  Progress: {j.get('progress', 0)}")
    logs = j.get('logs', [])
    if logs:
        print(f"  Last logs:")
        for log in logs[-5:]:
            print(f"    {log}")
    print()
