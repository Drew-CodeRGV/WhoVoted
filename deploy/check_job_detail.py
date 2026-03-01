import json

with open('/opt/whovoted/data/processing_jobs.json') as f:
    jobs = json.load(f)

for jid, j in jobs.items():
    print(f"Job: {jid}")
    print(f"  File: {j.get('original_filename', '?')}")
    print(f"  Status: {j['status']}")
    print(f"  Progress: {j['progress']}")
    print(f"  Processed: {j['processed_records']}/{j['total_records']}")
    print(f"  Cache: {j.get('cache_hits', 0)}")
    print(f"  County: {j.get('county')}, Year: {j.get('year')}, Type: {j.get('election_type')}")
    print(f"  Party: {j.get('primary_party')}, Method: {j.get('voting_method')}")
    print()
