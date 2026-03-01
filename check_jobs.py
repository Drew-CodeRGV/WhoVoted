import json
with open('/opt/whovoted/data/processing_jobs.json') as f:
    d = json.load(f)
for k, v in d.items():
    print(f"Job {k}:")
    print(f"  status: {v.get('status')}")
    print(f"  file: {v.get('original_filename')}")
    print(f"  processed: {v.get('processed_records')}/{v.get('total_records')}")
    print(f"  geocoded: {v.get('geocoded_count')}")
    print(f"  started: {v.get('started_at')}")
    print(f"  completed: {v.get('completed_at')}")
