#!/usr/bin/env python3
import requests

BASE = 'https://politiquera.com'

for url in ['/api/elections?county=Hidalgo', '/api/election-stats?county=Hidalgo&election_date=2026-03-03']:
    print(f"\n=== {url} ===")
    r = requests.get(f'{BASE}{url}')
    print(f"Status: {r.status_code}")
    print(f"Content-Type: {r.headers.get('Content-Type', 'N/A')}")
    print(f"Body (first 500 chars): {r.text[:500]}")
