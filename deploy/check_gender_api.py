#!/usr/bin/env python3
"""Quick check of gender fields in election-insights API."""
import urllib.request
import json

resp = urllib.request.urlopen('http://localhost:5000/api/election-insights')
d = json.loads(resp.read())

print("=== Election Insights Gender Stats ===")
print(f"Female 2026: {d.get('female_2026')}")
print(f"Male 2026: {d.get('male_2026')}")
print(f"DEM Female: {d.get('dem_female_2026')}")
print(f"DEM Male: {d.get('dem_male_2026')}")
print(f"REP Female: {d.get('rep_female_2026')}")
print(f"REP Male: {d.get('rep_male_2026')}")
print(f"Total EV 2026: {d.get('ev_2026')}")
