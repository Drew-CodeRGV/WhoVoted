#!/usr/bin/env python3
"""Check what /admin/status returns by reading jobs file directly."""
import json

with open('/opt/whovoted/data/processing_jobs.json') as f:
    jobs = json.load(f)

active = 0
queued = 0
for jid, j in jobs.items():
    status = j.get('status', 'unknown')
    fname = j.get('original_filename', 'N/A')[:50]
    total = j.get('total_records', 0)
    processed = j.get('processed_records', 0)
    progress = j.get('progress', 0)
    print(f"{jid[:8]} | {status:10} | {progress:.0%} | {processed}/{total} | {fname}")
    if status == 'running':
        active += 1
    elif status == 'queued':
        queued += 1

print(f"\nActive: {active}, Queued: {queued}")

# Check if auto-complete would trigger
for jid, j in jobs.items():
    if j.get('status') == 'running' and j.get('total_records', 0) > 0:
        if j.get('processed_records', 0) >= j.get('total_records', 0):
            print(f"\nWARNING: Job {jid[:8]} would be auto-completed (processed >= total)")
