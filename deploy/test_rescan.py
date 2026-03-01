import requests, json

s = requests.Session()
r = s.post('http://127.0.0.1:5000/admin/login', json={'username': 'admin', 'password': 'admin2026!'})
print(f"Login: {r.status_code}")

r = s.post('http://127.0.0.1:5000/admin/rescan')
print(f"Rescan POST: {r.status_code}")
print(r.text[:500])
