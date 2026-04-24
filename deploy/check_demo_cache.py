#!/usr/bin/env python3
import json
d = json.load(open('/opt/whovoted/public/cache/misdbond2026_demographics.json'))
print('Keys:', list(d.keys()))
print('zone_groups:', d.get('zone_groups', 'MISSING'))
print('zones count:', len(d.get('zones', {})))
if 'zones' in d:
    for z in list(d['zones'].keys())[:5]:
        print(f'  {z}: voted={d["zones"][z]["total_voted"]}')
