#!/usr/bin/env python3
import json, glob, os

# Check the latest job for the file path
jobs_file = '/opt/whovoted/data/processing_jobs.json'
with open(jobs_file) as f:
    jobs = json.load(f)

# Find the DEM 2026 job
for jid, job in sorted(jobs.items(), key=lambda x: x[1].get('created_at', ''), reverse=True):
    if 'DEM' in (job.get('original_filename') or '').upper() and '2026' in (job.get('original_filename') or ''):
        print(f"Job: {jid}")
        print(f"File: {job.get('original_filename')}")
        print(f"CSV path: {job.get('csv_path')}")
        csv_path = job.get('csv_path')
        if csv_path and os.path.exists(csv_path):
            import pandas as pd
            df = pd.read_excel(csv_path) if csv_path.endswith('.xlsx') else pd.read_csv(csv_path)
            print(f"Columns: {list(df.columns)}")
            print(f"Shape: {df.shape}")
            print(f"First row: {dict(df.iloc[0])}")
        else:
            print(f"File not found at {csv_path}")
            # Try uploads dir
            uploads = glob.glob('/opt/whovoted/uploads/*DEM*2026*')
            if uploads:
                print(f"Found in uploads: {uploads}")
                for u in uploads:
                    df = pd.read_excel(u) if u.endswith('.xlsx') else pd.read_csv(u)
                    print(f"  Columns: {list(df.columns)}")
                    print(f"  Shape: {df.shape}")
        break
