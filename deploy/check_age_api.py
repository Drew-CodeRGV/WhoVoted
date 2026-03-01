#!/usr/bin/env python3
"""Quick check of age group fields in election-insights API."""
import urllib.request
import json

resp = urllib.request.urlopen('http://localhost:5000/api/election-insights')
d = json.loads(resp.read())

print("=== Election Insights Age Groups ===")
ag = d.get('age_groups_2026', {})
order = ['18-24','25-34','35-44','45-54','55-64','65-74','75+','Unknown']
total_all = 0
for group in order:
    data = ag.get(group, {})
    t = data.get('total', 0)
    dem = data.get('dem', 0)
    rep = data.get('rep', 0)
    total_all += t
    pct = round(dem/(dem+rep)*100) if (dem+rep) else 0
    print(f"  {group:>8}: {t:>6,} total  ({dem:>6,} D, {rep:>6,} R)  DEM {pct}%")
print(f"  {'TOTAL':>8}: {total_all:>6,}")
print(f"\nGender: F={d.get('female_2026')}, M={d.get('male_2026')}")
print(f"EV total: {d.get('ev_2026')}")
