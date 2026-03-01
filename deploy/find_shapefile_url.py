#!/usr/bin/env python3
import urllib.request
import json

url = 'https://data.capitol.texas.gov/api/3/action/package_show?id=planc2333'
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=15)
data = json.loads(resp.read())
for r in data['result']['resources']:
    name = r.get('name', '')
    desc = r.get('description', '')
    dl = r.get('url', '')
    fmt = r.get('format', '')
    if 'PLANC2333.zip' in name or 'Shapefile' in desc.lower() or (fmt == 'ZIP' and 'PLANC2333' in name and 'blk' not in name.lower() and 'All_Files' not in name):
        print(f"Found: {name}")
        print(f"URL: {dl}")
        print(f"Format: {fmt}")
        break
else:
    print("Shapefile resource not found. All resources:")
    for r in data['result']['resources']:
        print(f"  {r.get('name','')} | {r.get('format','')} | {r.get('url','')[:100]}")
