#!/usr/bin/env python3
"""Update processing_jobs.json to reflect the backfilled coordinates for 2026 datasets."""
import json

jobs_file = '/opt/whovoted/data/processing_jobs.json'
with open(jobs_file, 'r') as f:
    jobs = json.load(f)

updated = 0
for job_id, job in jobs.items():
    year = job.get('year', '')
    fn = job.get('original_filename', '')
    
    if year == '2026' or '2026' in fn:
        old_geo = job.get('geocoded_count', 0)
        old_fail = job.get('failed_count', 0)
        total = job.get('total_records', 0)
        
        # Read the actual map_data file to count coords
        map_file = None
        vm = job.get('voting_method', '')
        pp = job.get('primary_party', '')
        
        # Find the map_data file for this job
        data_dir = '/opt/whovoted/public/data'
        import glob
        for mf in glob.glob(f'{data_dir}/map_data_*2026*.json'):
            # Match by party
            if pp and pp.lower() in mf.lower():
                map_file = mf
                break
        
        if not map_file:
            print(f"  Could not find map_data for job {fn}")
            continue
        
        with open(map_file, 'r') as f:
            geojson = json.load(f)
        
        features = geojson.get('features', [])
        has_coords = 0
        no_coords = 0
        for feat in features:
            geom = feat.get('geometry')
            coords = geom.get('coordinates', []) if geom else []
            if coords and len(coords) >= 2 and coords[0] != 0 and coords[1] != 0:
                has_coords += 1
            else:
                no_coords += 1
        
        print(f"  {fn}: was geo={old_geo} fail={old_fail}, now geo={has_coords} fail={no_coords}")
        job['geocoded_count'] = has_coords
        job['failed_count'] = no_coords
        updated += 1

if updated > 0:
    with open(jobs_file, 'w') as f:
        json.dump(jobs, f, indent=2)
    print(f"\nUpdated {updated} jobs in processing_jobs.json")
else:
    print("No 2026 jobs found to update")
