import requests, json

s = requests.Session()
s.post('http://127.0.0.1:5000/admin/login', json={'username': 'admin', 'password': 'admin2026!'})
r = s.get('http://127.0.0.1:5000/admin/status')
data = r.json()
for j in data.get('jobs', []):
    print(f"{j.get('original_filename')}: {j.get('status')} {j.get('processed_records')}/{j.get('total_records')} cache={j.get('cache_hits',0)}")
if not data.get('jobs'):
    print(f"No jobs. Status: {data.get('status', 'unknown')}")
