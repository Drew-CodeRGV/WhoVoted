#!/usr/bin/env python3
"""Check the last import details from processing jobs."""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
JOBS_FILE = '/opt/whovoted/data/processing_jobs.json'

print("="*70)
print("LAST IMPORT ANALYSIS")
print("="*70)

# Check processing jobs
if Path(JOBS_FILE).exists():
    with open(JOBS_FILE, 'r') as f:
        jobs = json.load(f)
    
    # Find most recent Hidalgo 2026 job
    hidalgo_2026_jobs = [
        (job_id, job) for job_id, job in jobs.items()
        if 'Hidalgo' in job.get('filename', '') and '2026' in job.get('filename', '')
    ]
    
    if hidalgo_2026_jobs:
        print(f"\nFound {len(hidalgo_2026_jobs)} Hidalgo 2026 import jobs:")
        
        for job_id, job in sorted(hidalgo_2026_jobs, key=lambda x: x[1].get('started_at', 0), reverse=True)[:5]:
            print(f"\nJob ID: {job_id}")
            print(f"  Filename: {job.get('filename', 'N/A')}")
            print(f"  Status: {job.get('status', 'N/A')}")
            print(f"  Started: {datetime.fromtimestamp(job.get('started_at', 0)).strftime('%Y-%m-%d %H:%M:%S') if job.get('started_at') else 'N/A'}")
            print(f"  Completed: {datetime.fromtimestamp(job.get('completed_at', 0)).strftime('%Y-%m-%d %H:%M:%S') if job.get('completed_at') else 'N/A'}")
            print(f"  Records processed: {job.get('records_processed', 0):,}")
            print(f"  Records imported: {job.get('records_imported', 0):,}")
            print(f"  Errors: {job.get('error_count', 0):,}")
            
            if job.get('error'):
                print(f"  Error message: {job['error']}")
    else:
        print("\n⚠️  No Hidalgo 2026 jobs found in processing_jobs.json")
else:
    print(f"\n⚠️  Processing jobs file not found: {JOBS_FILE}")

# Check database for import metadata
print("\n" + "="*70)
print("DATABASE RECORDS")
print("="*70)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Check when records were last updated
result = conn.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(DISTINCT ve.vuid) as unique_vuids,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
      AND ve.election_date = '2026-03-03'
""").fetchone()

print(f"\nHidalgo County 2026-03-03:")
print(f"  Total records: {result['total']:,}")
print(f"  Unique VUIDs: {result['unique_vuids']:,}")
print(f"  Democratic: {result['dem']:,}")
print(f"  Republican: {result['rep']:,}")
print(f"  Total with party: {result['dem'] + result['rep']:,}")

# Check for records without county
no_county = conn.execute("""
    SELECT COUNT(*) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE (v.county IS NULL OR v.county = '')
      AND ve.election_date = '2026-03-03'
""").fetchone()['cnt']

if no_county > 0:
    print(f"\n⚠️  {no_county:,} records have no county assigned")

# Check uploaded files
print("\n" + "="*70)
print("UPLOADED FILES")
print("="*70)

uploads_dir = Path('/opt/whovoted/uploads')
if uploads_dir.exists():
    files = sorted(uploads_dir.glob('*2026*'), key=lambda x: x.stat().st_mtime, reverse=True)
    if files:
        print(f"\nFound {len(files)} files with '2026' in name:")
        for f in files[:10]:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            size = f.stat().st_size / 1024 / 1024  # MB
            print(f"  {f.name}")
            print(f"    Modified: {mtime.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"    Size: {size:.2f} MB")
    else:
        print("\n⚠️  No files with '2026' found in uploads directory")
else:
    print(f"\n⚠️  Uploads directory not found: {uploads_dir}")

conn.close()

print("\n" + "="*70)
print("\nRECOMMENDATIONS:")
print("1. Download latest data from Texas SOS website")
print("2. Upload via admin panel to refresh the data")
print("3. Run verify_sos_data.py to compare with official numbers")
print("="*70)
