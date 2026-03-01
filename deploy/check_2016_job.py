#!/usr/bin/env python3
import json

with open('/opt/whovoted/data/processing_jobs.json') as f:
    jobs = json.load(f)

# Find the 2016 job
for jid, j in jobs.items():
    fn = j.get('original_filename', '')
    if '2016' in fn:
        print(f"Job: {jid}")
        print(f"File: {fn}")
        print(f"Status: {j.get('status')}")
        print(f"Total: {j.get('total_records', 0):,}")
        print(f"Processed: {j.get('processed_records', 0):,}")
        print(f"Geocoded: {j.get('geocoded_count', 0):,}")
        print(f"Failed/Unmatched: {j.get('failed_count', 0):,}")
        print(f"Progress: {j.get('progress', 0)*100:.1f}%")
        print()
        
        # Show relevant log lines
        logs = j.get('logs', [])
        for line in logs:
            if any(kw in line.lower() for kw in ['unmatched', 'geocod', 'db hit', 'not found', 'miss', 'step 2', 'newly', 'coverage', 'voter db']):
                print(f"  {line}")
        
        print(f"\nLast 20 log lines:")
        for line in logs[-20:]:
            print(f"  {line}")
        break
