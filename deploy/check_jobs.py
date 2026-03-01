#!/usr/bin/env python3
import json

with open('/opt/whovoted/data/processing_jobs.json') as f:
    jobs = json.load(f)

for jid, j in jobs.items():
    print(f"Job {jid[:8]}:")
    print(f"  file: {j.get('original_filename')}")
    print(f"  status: {j.get('status')}")
    print(f"  progress: {j.get('progress')}")
    print(f"  total: {j.get('total_records')}")
    print(f"  processed: {j.get('processed_records')}")
    print()
