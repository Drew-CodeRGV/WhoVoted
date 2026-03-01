#!/usr/bin/env python3
import json, urllib.request
resp = urllib.request.urlopen("http://localhost:5000/api/election-insights")
d = json.loads(resp.read())
nag = d.get("new_age_gender_2026", {})
print("New voter age groups (2026):")
sorted_groups = sorted(nag.items(), key=lambda x: x[1]["total"], reverse=True)
for age, v in sorted_groups:
    print(f"  {age:10s} total={v['total']:6d}  female={v.get('female',0):5d}  male={v.get('male',0):5d}")
print(f"\nTotal new voters: {d.get('new_2026', 0)}")
print(f"Top 3: {[g[0] for g in sorted_groups[:3]]}")
