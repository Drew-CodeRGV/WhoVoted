#!/bin/bash
cd /opt/whovoted
python3 -c "
import json
d = json.load(open('data/processing_jobs.json'))
if not d:
    print('No jobs')
else:
    for jid, j in d.items():
        print(f'Job: {j.get(\"original_filename\",\"?\")}')
        print(f'  Status: {j.get(\"status\",\"?\")}')
        print(f'  Progress: {j.get(\"processed_records\",0)}/{j.get(\"total_records\",0)}')
        print(f'  Cached: {j.get(\"cache_hits\",0)}')
        print(f'  Geocoded: {j.get(\"geocoded_count\",0)}')
        print(f'  Failed: {j.get(\"failed_count\",0)}')
"
