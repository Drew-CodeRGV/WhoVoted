#!/usr/bin/env python3
import json, urllib.request

# Test multi-county voter fetch
url = 'http://localhost:5000/api/voters?county=Hidalgo,Brooks&election_date=2026-03-03'
data = json.loads(urllib.request.urlopen(url).read())
total = len(data['features'])
geocoded = sum(1 for f in data['features'] if f['geometry'] is not None)
print(f"Multi-county (Hidalgo+Brooks) 2026: {total} voters, {geocoded} geocoded")

# Test single county
url2 = 'http://localhost:5000/api/voters?county=Brooks&election_date=2026-03-03'
data2 = json.loads(urllib.request.urlopen(url2).read())
print(f"Brooks only 2026: {len(data2['features'])} voters")

url3 = 'http://localhost:5000/api/voters?county=Hidalgo&election_date=2026-03-03'
data3 = json.loads(urllib.request.urlopen(url3).read())
print(f"Hidalgo only 2026: {len(data3['features'])} voters")
print(f"Sum: {len(data2['features']) + len(data3['features'])}")
