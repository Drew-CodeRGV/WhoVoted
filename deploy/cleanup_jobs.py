import json

jobs_file = '/opt/whovoted/data/processing_jobs.json'
with open(jobs_file, 'r') as f:
    jobs = json.load(f)

for jid, job in jobs.items():
    if job.get('status') == 'running':
        job['status'] = 'failed'
        job['errors'] = ['Server restarted during processing - please re-upload']
        print(f"Marked job {jid} as failed")

with open(jobs_file, 'w') as f:
    json.dump(jobs, f, indent=2)

print("Done")
