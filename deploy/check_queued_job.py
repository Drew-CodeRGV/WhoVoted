#!/usr/bin/env python3
"""Check details of queued jobs and whether their files still exist."""
import json
import os

with open('/opt/whovoted/data/processing_jobs.json') as f:
    jobs = json.load(f)

for jid, j in jobs.items():
    if j.get('status') == 'queued':
        print(f"Job: {jid}")
        print(f"  File: {j.get('original_filename', 'N/A')}")
        # Check if csv_path is stored
        csv_path = j.get('csv_path', 'NOT STORED')
        print(f"  csv_path: {csv_path}")
        if csv_path != 'NOT STORED' and os.path.exists(csv_path):
            print(f"  File exists: YES ({os.path.getsize(csv_path)} bytes)")
        elif csv_path != 'NOT STORED':
            print(f"  File exists: NO")
        
        # Print all keys
        print(f"  Keys: {list(j.keys())}")
        print(f"  County: {j.get('county')}")
        print(f"  Year: {j.get('year')}")
        print(f"  Election type: {j.get('election_type')}")
        print(f"  Voting method: {j.get('voting_method')}")
        print(f"  Primary party: {j.get('primary_party')}")
        print(f"  Election date: {j.get('election_date')}")

# Also check uploads directory
uploads_dir = '/opt/whovoted/uploads'
if os.path.exists(uploads_dir):
    files = os.listdir(uploads_dir)
    print(f"\nUploads directory ({len(files)} files):")
    for f in sorted(files)[-5:]:
        fpath = os.path.join(uploads_dir, f)
        print(f"  {f} ({os.path.getsize(fpath)} bytes)")
