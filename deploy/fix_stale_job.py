import json
from datetime import datetime

jobs_file = '/opt/whovoted/data/processing_jobs.json'
with open(jobs_file) as f:
    jobs = json.load(f)

for jid, j in jobs.items():
    if j['status'] == 'running' and j['processed_records'] >= j['total_records']:
        j['status'] = 'completed'
        j['progress'] = 1.0
        j['completed_at'] = datetime.now().isoformat()
        print(f"Fixed job {jid}: marked as completed (was stuck at {j.get('progress')})")

with open(jobs_file, 'w') as f:
    json.dump(jobs, f, indent=2)

print("Done")
