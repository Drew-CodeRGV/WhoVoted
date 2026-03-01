#!/usr/bin/env python3
"""Check active processing jobs."""
import json, os
jobs_file = '/opt/whovoted/data/processing_jobs.json'
if not os.path.exists(jobs_file):
    print("No jobs file found")
    exit()
with open(jobs_file) as f:
    data = json.load(f)

if isinstance(data, dict):
    jobs = list(data.values())
elif isinstance(data, list):
    jobs = data
else:
    print(f"Unexpected format: {type(data)}")
    exit()

for j in jobs:
    if isinstance(j, str):
        print(f"  String entry: {j}")
        continue
    status = j.get('status', '?')
    processed = j.get('processed', 0)
    total = j.get('total', 0)
    fn = j.get('filename', '?')
    jid = j.get('id', '?')[:12]
    print(f"  {jid} | {status} | {processed}/{total} | {fn}")
