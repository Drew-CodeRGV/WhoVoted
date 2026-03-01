import json

with open('/opt/whovoted/data/processing_jobs.json') as f:
    jobs = json.load(f)

for jid, j in jobs.items():
    print(f"Job: {jid}")
    print(f"  Status: {j['status']}")
    print(f"  Progress: {j['progress']}")
    print(f"  Processed: {j['processed_records']}/{j['total_records']}")
    print(f"  Cache hits: {j.get('cache_hits', 0)}")
    print(f"  Geocoded: {j.get('geocoded_count', 0)}")
    print(f"  Failed: {j.get('failed_count', 0)}")
    print(f"  Completed at: {j.get('completed_at', 'None')}")
