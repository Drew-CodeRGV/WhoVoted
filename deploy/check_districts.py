#!/usr/bin/env python3
import json

d = json.load(open('/opt/whovoted/public/data/districts.json'))
for f in d['features']:
    p = f['properties']
    geom = f['geometry']
    coords_count = 0
    if geom['type'] == 'Polygon':
        coords_count = len(geom['coordinates'][0])
    elif geom['type'] == 'MultiPolygon':
        coords_count = sum(len(ring[0]) for ring in geom['coordinates'])
    print(f"{p['district_id']:10s} {p['district_type']:15s} {p['district_name']:30s} coords={coords_count}")
