#!/usr/bin/env python3
"""Test the new DB-driven endpoints."""
import requests

base = 'http://localhost:5000'
session = requests.Session()

# Login with form data
r = session.post(f'{base}/admin/login', data={'username': 'admin', 'password': 'admin2026!'}, allow_redirects=False)
print(f"Login: {r.status_code} (302 = success)")

# Election datasets
r = session.get(f'{base}/admin/election-datasets')
print(f"\nElection datasets: {r.status_code}")
if r.status_code == 200:
    try:
        data = r.json()
        print(f"  Count: {len(data)}")
        for d in data:
            print(f"  {d['election_date']} | {d['party_voted']:12s} | {d['voting_method']:15s} | "
                  f"total={d['total_voters']:>6,} geo={d['geocoded_count']:>6,} ungeo={d['ungeocoded_count']:>6,} | {d['county']}")
    except Exception as e:
        print(f"  Response: {r.text[:500]}")
else:
    print(f"  Response: {r.text[:200]}")

# Election summary
r = session.get(f'{base}/admin/election-summary')
print(f"\nElection summary: {r.status_code}")
if r.status_code == 200:
    try:
        summary = r.json()
        for k, v in summary.items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"  Response: {r.text[:500]}")
