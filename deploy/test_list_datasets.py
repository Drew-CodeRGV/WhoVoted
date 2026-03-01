#!/usr/bin/env python3
"""Test list-datasets endpoint."""
import requests

s = requests.Session()
# Login
r = s.post('http://localhost:5000/admin/login', data={'username': 'admin', 'password': 'admin2026!'})
print(f"Login: {r.status_code}")

# List datasets
r = s.get('http://localhost:5000/admin/list-datasets')
print(f"List: {r.status_code}")
data = r.json()
print(f"Success: {data.get('success')}")
print(f"Datasets: {len(data.get('datasets', []))}")
for ds in data.get('datasets', []):
    print(f"  {ds['mapDataFile']} | {ds['votingMethod']} | {ds['totalAddresses']} records")
