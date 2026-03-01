"""Re-submit the DEM ED 03012022.xlsx file for processing."""
import requests
import json
import os

SERVER = 'http://127.0.0.1:5000'
SESSION = requests.Session()

# Login
login_resp = SESSION.post(f'{SERVER}/admin/login', json={
    'username': 'admin',
    'password': 'admin2026!'
})
print(f"Login: {login_resp.status_code}")
if login_resp.status_code != 200:
    exit(1)

# Clean stale jobs
jobs_file = '/opt/whovoted/data/processing_jobs.json'
with open(jobs_file) as f:
    jobs = json.load(f)
for jid in list(jobs.keys()):
    if jobs[jid]['status'] == 'running':
        jobs[jid]['status'] = 'failed'
        print(f"Marked stale job {jid} as failed")
with open(jobs_file, 'w') as f:
    json.dump(jobs, f, indent=2)

# Find the file
dem_file = '/opt/whovoted/uploads/6d70031a-fb72-4295-b5f6-a01a77049cbe_DEM_ED_03012022.xlsx'

print(f"Re-uploading: {dem_file}")

with open(dem_file, 'rb') as f:
    resp = SESSION.post(f'{SERVER}/admin/upload', 
        files={
            'files': ('DEM ED 03012022.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        },
        data={
            'county': 'Hidalgo',
            'year': '2022',
            'election_type': 'primary',
            'election_date': '2022-03-01',
            'voting_method': 'election-day',
            'primary_party': 'democratic',
            'duplicate_action': 'replace',
            'processing_speed': '10'
        }
    )

print(f"Upload: {resp.status_code}")
try:
    print(json.dumps(resp.json(), indent=2))
except:
    print(resp.text[:500])
