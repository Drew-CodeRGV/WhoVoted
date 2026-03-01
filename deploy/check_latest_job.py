#!/usr/bin/env python3
import json, glob, os

# Check processing_jobs.json for latest job
jobs_file = '/opt/whovoted/data/processing_jobs.json'
if os.path.exists(jobs_file):
    with open(jobs_file) as f:
        jobs = json.load(f)
    for jid, job in sorted(jobs.items(), key=lambda x: x[1].get('created_at', ''), reverse=True)[:3]:
        print(f"\n=== Job {jid} ===")
        print(f"  File: {job.get('original_filename')}")
        print(f"  Status: {job.get('status')}")
        print(f"  Total: {job.get('total_records')}")
        print(f"  Processed: {job.get('processed_records')}")
        print(f"  Geocoded: {job.get('geocoded_count')}")
        print(f"  Failed: {job.get('failed_count')}")
        print(f"  Cache hits: {job.get('cache_hits')}")
        print(f"  Is EV: {job.get('is_early_voting')}")
        errs = job.get('errors', [])
        if errs:
            print(f"  Errors ({len(errs)}):")
            for e in errs[:5]:
                print(f"    {e}")

# Check processing_errors.csv
errors_csv = '/opt/whovoted/data/processing_errors.csv'
if os.path.exists(errors_csv):
    with open(errors_csv) as f:
        lines = f.readlines()
    print(f"\n=== processing_errors.csv: {len(lines)} lines ===")
    for line in lines[:10]:
        print(f"  {line.strip()}")

# Check the latest EV geojson for unmatched count
geojson_files = glob.glob('/opt/whovoted/public/data/map_data_*2026*dem*.json')
for gf in sorted(geojson_files):
    with open(gf) as f:
        data = json.load(f)
    feats = data.get('features', [])
    unmatched = sum(1 for f in feats if f.get('properties', {}).get('unmatched'))
    geocoded = sum(1 for f in feats if f.get('geometry'))
    no_geom = sum(1 for f in feats if not f.get('geometry'))
    print(f"\n=== {os.path.basename(gf)} ===")
    print(f"  Total features: {len(feats)}")
    print(f"  With geometry: {geocoded}")
    print(f"  No geometry (unmatched): {no_geom}")
    print(f"  Unmatched flag: {unmatched}")
