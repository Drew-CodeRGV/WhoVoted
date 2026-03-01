#!/usr/bin/env python3
"""Quick check of gender fields in district-stats API."""
import urllib.request
import json
import sqlite3

# Get a few VUIDs from the DB to test with
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
vuids = [r[0] for r in conn.execute(
    "SELECT vuid FROM voter_elections WHERE election_date='2026-03-03' LIMIT 100"
).fetchall()]
conn.close()

data = json.dumps({'vuids': vuids, 'district_id': 'test', 'election_date': '2026-03-03'}).encode()
req = urllib.request.Request(
    'http://localhost:5000/api/district-stats?district_id=test&election_date=2026-03-03',
    data=data,
    headers={'Content-Type': 'application/json'},
    method='POST'
)
resp = urllib.request.urlopen(req)
d = json.loads(resp.read())

print("=== District Stats Gender (100 sample VUIDs) ===")
print(f"Total: {d.get('total')}")
print(f"Female: {d.get('female')}")
print(f"Male: {d.get('male')}")
print(f"DEM Female: {d.get('dem_female')}")
print(f"DEM Male: {d.get('dem_male')}")
print(f"REP Female: {d.get('rep_female')}")
print(f"REP Male: {d.get('rep_male')}")
