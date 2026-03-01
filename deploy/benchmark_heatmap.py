#!/usr/bin/env python3
"""Benchmark heatmap endpoint vs full GeoJSON."""
import time
import urllib.request

BASE = "http://localhost:5000"
PARAMS = "county=Brooks,Hidalgo&election_date=2026-03-03&voting_method=early-voting"

print("=== Cold load (first call) ===")
for path, label in [
    (f"/api/voters/heatmap?{PARAMS}", "Heatmap (lightweight)"),
    (f"/api/voters?{PARAMS}", "Full GeoJSON"),
]:
    t0 = time.time()
    resp = urllib.request.urlopen(BASE + path)
    data = resp.read()
    elapsed = time.time() - t0
    size_mb = len(data) / 1024 / 1024
    print(f"  {label:25s}  {elapsed:6.2f}s  {size_mb:5.2f} MB")

print("\n=== Warm cache (second call) ===")
for path, label in [
    (f"/api/voters/heatmap?{PARAMS}", "Heatmap (lightweight)"),
    (f"/api/voters?{PARAMS}", "Full GeoJSON"),
]:
    t0 = time.time()
    resp = urllib.request.urlopen(BASE + path)
    data = resp.read()
    elapsed = time.time() - t0
    size_mb = len(data) / 1024 / 1024
    print(f"  {label:25s}  {elapsed:6.2f}s  {size_mb:5.2f} MB")
