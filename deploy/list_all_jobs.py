#!/usr/bin/env python3
"""List all jobs with their key fields."""
import json

with open('/opt/whovoted/data/processing_jobs.json', 'r') as f:
    jobs = json.load(f)

for job_id, job in jobs.items():
    fn = job.get('original_filename', '?')
    year = job.get('year', '?')
    geo = job.get('geocoded_count', 0)
    fail = job.get('failed_count', 0)
    total = job.get('total_records', 0)
    pp = job.get('primary_party', '')
    vm = job.get('voting_method', '')
    print(f"  [{year}] {fn[:55]:55s} | total={total:>6,} geo={geo:>6,} fail={fail:>6,} | {pp} {vm}")
