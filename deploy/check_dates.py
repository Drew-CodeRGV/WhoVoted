#!/usr/bin/env python3
import sys, os
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')
import database as db
db.init_db()
conn = db.get_connection()
rows = conn.execute("SELECT DISTINCT election_date, COUNT(*) FROM voter_elections GROUP BY election_date ORDER BY election_date").fetchall()
for r in rows:
    print(r[0], r[1])

# Check the GeoJSON files that were deployed
import glob
print("\nGeoJSON files in public/data:")
for f in sorted(glob.glob('/opt/whovoted/public/data/map_data_*2026*.json')):
    import json
    with open(f) as fh:
        data = json.load(fh)
    features = data.get('features', [])
    geocoded = sum(1 for feat in features if feat.get('geometry') is not None)
    print(f"  {os.path.basename(f)}: {len(features)} features, {geocoded} geocoded")

# Check the processing_jobs.json for the recent uploads
print("\nRecent jobs:")
import json
jobs_file = '/opt/whovoted/data/processing_jobs.json'
if os.path.exists(jobs_file):
    with open(jobs_file) as f:
        jobs = json.load(f)
    for jid, j in sorted(jobs.items(), key=lambda x: x[1].get('started_at', '')):
        if '2026' in str(j.get('year', '')):
            print(f"  {jid[:8]}... {j.get('original_filename', '?')} status={j.get('status')} "
                  f"total={j.get('total_records')} geocoded={j.get('geocoded_count')} failed={j.get('failed_count')}")
