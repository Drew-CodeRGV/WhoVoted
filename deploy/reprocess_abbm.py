#!/usr/bin/env python3
"""Reprocess ABBM files with mail-in voting method."""
import sys
import os
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted')

from processor import ProcessingJob

# ABBM files on server
files = {
    'DEM': '/opt/whovoted/uploads/8bd208f9-f4da-4fd5-a8e8-a88b66762861_ABBM20LIST20March2032020262028Cumulative2920DEM_202602270701392672.xlsx',
    'REP': '/opt/whovoted/uploads/7e5f6245-4da1-47ce-8255-979f55a46e64_ABBM20LIST20March2032020262028Cumulative2920REP_202602270702047956.xlsx',
}

# Check which files exist
for party, path in files.items():
    if os.path.exists(path):
        print(f"Found {party}: {path} ({os.path.getsize(path):,} bytes)")
    else:
        print(f"NOT FOUND {party}: {path}")

# If files not found with that exact name, search for them
upload_dir = '/opt/whovoted/uploads'
abbm_files = {}
for f in os.listdir(upload_dir):
    if 'ABBM' in f or 'abbm' in f:
        full = os.path.join(upload_dir, f)
        if 'DEM' in f.upper():
            abbm_files['DEM'] = full
        elif 'REP' in f.upper():
            abbm_files['REP'] = full
        print(f"Found ABBM file: {f}")

if not abbm_files:
    print("No ABBM files found in uploads directory!")
    sys.exit(1)

# Process each file
for party_key, filepath in sorted(abbm_files.items()):
    party = 'democratic' if party_key == 'DEM' else 'republican'
    print(f"\n{'='*60}")
    print(f"Processing {party_key} ABBM file as mail-in ballots")
    print(f"File: {filepath}")
    print(f"{'='*60}")
    
    job = ProcessingJob(
        csv_path=filepath,
        year='2026',
        county='Hidalgo',
        election_type='primary',
        election_date='2026-03-03',
        voting_method='mail-in',
        original_filename=os.path.basename(filepath),
        primary_party=party,
        max_workers=20,
    )
    
    try:
        job.run()
        print(f"\n{party_key} completed: {job.processed_records} records processed")
        for msg in job.log_messages[-5:]:
            print(f"  {msg}")
    except Exception as e:
        print(f"\n{party_key} FAILED: {e}")
        for msg in job.log_messages[-10:]:
            print(f"  {msg}")

print("\nDone!")
