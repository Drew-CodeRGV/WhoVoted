#!/usr/bin/env python3
"""Benchmark the cold page load API calls."""
import time
import urllib.request
import json

BASE = "http://localhost:5000"

endpoints = [
    ("/api/elections", "Elections list"),
    ("/api/voters?county=Brooks,Hidalgo&election_date=2026-03-03&voting_method=early-voting", "Voters GeoJSON (51K)"),
    ("/api/election-stats?county=Brooks,Hidalgo&election_date=2026-03-03&voting_method=early-voting", "Election stats"),
]

for path, label in endpoints:
    url = BASE + path
    t0 = time.time()
    resp = urllib.request.urlopen(url)
    data = resp.read()
    elapsed = time.time() - t0
    size_mb = len(data) / 1024 / 1024
    print(f"{label:30s}  {elapsed:6.2f}s  {size_mb:5.1f} MB")

# Second call (cached)
print("\n--- Cached (2nd call) ---")
for path, label in endpoints:
    url = BASE + path
    t0 = time.time()
    resp = urllib.request.urlopen(url)
    data = resp.read()
    elapsed = time.time() - t0
    size_mb = len(data) / 1024 / 1024
    print(f"{label:30s}  {elapsed:6.2f}s  {size_mb:5.1f} MB")
