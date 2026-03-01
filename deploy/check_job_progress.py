#!/usr/bin/env python3
import json, os, time
from datetime import datetime

jobs_file = '/opt/whovoted/data/processing_jobs.json'
if not os.path.exists(jobs_file):
    print("No jobs file found")
    exit()

with open(jobs_file) as f:
    jobs = json.load(f)

# Find active or most recent job
active = [v for v in jobs.values() if v.get('status') in ('processing', 'running')]
if not active:
    # Show most recent job
    all_jobs = sorted(jobs.values(), key=lambda x: x.get('started_at', ''), reverse=True)
    if all_jobs:
        j = all_jobs[0]
        print(f"Most recent job: {j.get('status', 'unknown')}")
        print(f"  File: {j.get('original_filename', 'unknown')}")
        print(f"  Started: {j.get('started_at', '?')}")
        print(f"  Completed: {j.get('completed_at', '?')}")
        print(f"  Progress: {j.get('progress', 0)*100:.1f}%")
        print(f"  Total records: {j.get('total_records', 0):,}")
        print(f"  Processed: {j.get('processed_records', 0):,}")
        print(f"  Geocoded: {j.get('geocoded_count', 0):,}")
        print(f"  Failed: {j.get('failed_count', 0):,}")
        logs = j.get('logs', [])
        if logs:
            print(f"\nLast 10 log lines:")
            for line in logs[-10:]:
                print(f"  {line}")
    else:
        print("No jobs found")
    exit()

j = active[0]
progress = j.get('progress', 0)
total = j.get('total_records', 0)
processed = j.get('processed_records', 0)
geocoded = j.get('geocoded_count', 0)
failed = j.get('failed_count', 0)
started = j.get('started_at', '')

print(f"ACTIVE JOB")
print(f"  File: {j.get('original_filename', 'unknown')}")
print(f"  Status: {j.get('status', 'unknown')}")
print(f"  Progress: {progress*100:.1f}%")
print(f"  Total records: {total:,}")
print(f"  Processed: {processed:,}")
print(f"  Geocoded: {geocoded:,}")
print(f"  Failed: {failed:,}")
print(f"  Started: {started}")

# Estimate time remaining
if started and processed > 0:
    try:
        start_dt = datetime.fromisoformat(started.replace('Z', '+00:00')) if 'Z' in started else datetime.fromisoformat(started)
        elapsed = (datetime.now() - start_dt).total_seconds()
        rate = processed / elapsed if elapsed > 0 else 0
        remaining = (total - processed) / rate if rate > 0 else 0
        print(f"\n  Elapsed: {elapsed/60:.1f} minutes")
        print(f"  Rate: {rate:.1f} records/sec")
        print(f"  Estimated remaining: {remaining/60:.1f} minutes")
    except Exception as e:
        print(f"  (Could not estimate time: {e})")

logs = j.get('logs', [])
if logs:
    print(f"\nLast 15 log lines:")
    for line in logs[-15:]:
        print(f"  {line}")
