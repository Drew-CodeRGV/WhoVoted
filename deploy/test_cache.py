#!/usr/bin/env python3
"""Test API response times to verify caching."""
import urllib.request
import time

def timed_fetch(url, label):
    t0 = time.time()
    resp = urllib.request.urlopen(url)
    data = resp.read()
    elapsed = time.time() - t0
    print(f"  {elapsed*1000:>7.1f}ms  {len(data):>8,} bytes  {label}")

print("=== First requests (cold cache) ===")
timed_fetch('http://localhost:5000/api/elections', '/api/elections')
timed_fetch('http://localhost:5000/api/election-stats?county=Hidalgo&election_date=2026-03-03&voting_method=early-voting', '/api/election-stats')

print("\n=== Second requests (warm cache) ===")
timed_fetch('http://localhost:5000/api/elections', '/api/elections')
timed_fetch('http://localhost:5000/api/election-stats?county=Hidalgo&election_date=2026-03-03&voting_method=early-voting', '/api/election-stats')

print("\n=== Third requests (warm cache) ===")
timed_fetch('http://localhost:5000/api/elections', '/api/elections')
timed_fetch('http://localhost:5000/api/election-stats?county=Hidalgo&election_date=2026-03-03&voting_method=early-voting', '/api/election-stats')
