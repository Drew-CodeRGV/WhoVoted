#!/usr/bin/env python3
"""Check processing_jobs.json to see what the upload history table shows."""
import json

with open('/opt/whovoted/data/processing_jobs.json', 'r') as f:
    jobs = json.load(f)

print(f"Total jobs: {len(jobs)}")
for j in jobs:
    fn = (j.get('original_filename') or '?')[:50]
    total = j.get('total_records', 0)
    geo = j.get('geocoded_count', 0)
    failed = j.get('failed_count', 0)
    year = j.get('year', '?')
    print(f"  {fn:50s} | {year} | total={total:,} geo={geo:,} fail={failed:,}")
