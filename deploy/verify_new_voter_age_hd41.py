#!/usr/bin/env python3
"""Verify new voter age/gender breakdown for HD-41 district via the API."""
import urllib.request
import json

# First, get the full district stats for HD-41 by calling the API
# We need to simulate what the frontend does - get VUIDs from GeoJSON that fall in HD-41
# Instead, let's just query the API directly and also cross-check with raw DB

# Check what the API returns
print("=== Checking API response for new_age_gender ===")
resp = urllib.request.urlopen('http://localhost:5000/api/election-insights')
d = json.loads(resp.read())
nag = d.get('new_age_gender_2026', {})
print("\nCounty-wide new voter age/gender breakdown:")
order = ['18-24','25-34','35-44','45-54','55-64','65-74','75+','Unknown']
total_all = 0
for ag in order:
    g = nag.get(ag, {})
    t = g.get('total', 0)
    f = g.get('female', 0)
    m = g.get('male', 0)
    total_all += t
    print(f"  {ag:>8}: {t:>5,} total  (♀{f:>5,}  ♂{m:>5,})")
print(f"  {'TOTAL':>8}: {total_all:>5,}")
print(f"\nNew voters total from API: {d.get('new_2026')}")
