#!/usr/bin/env python3
"""Verify new vs old congressional boundaries by testing known points."""
import json

def point_in_polygon(point, polygon):
    x, y = point
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def point_in_feature(lng, lat, feature):
    geom = feature['geometry']
    if geom['type'] == 'Polygon':
        return point_in_polygon([lng, lat], geom['coordinates'][0])
    elif geom['type'] == 'MultiPolygon':
        return any(point_in_polygon([lng, lat], poly[0]) for poly in geom['coordinates'])
    return False

# Test points in Hidalgo County
test_points = [
    ('McAllen City Hall', -98.2300, 26.2034),
    ('Edinburg Courthouse', -98.1631, 26.3017),
    ('Mission TX', -98.3253, 26.2159),
    ('Pharr TX', -98.1836, 26.1950),
    ('Weslaco TX', -97.9908, 26.1595),
]

new_districts = json.load(open('/opt/whovoted/public/data/districts.json'))
old_districts = json.load(open('/opt/whovoted/public/data/districts_old_congressional.json'))

new_cd = [f for f in new_districts['features'] if f['properties']['district_type'] == 'congressional']
old_cd = old_districts['features']

print("=== New Map (PlanC2333) ===")
for name, lng, lat in test_points:
    matches = [f['properties']['district_id'] for f in new_cd if point_in_feature(lng, lat, f)]
    print(f"  {name}: {matches or 'NONE'}")

print("\n=== Old Map (PlanC2193 / 119th Congress) ===")
for name, lng, lat in test_points:
    matches = [f['properties']['district_id'] for f in old_cd if point_in_feature(lng, lat, f)]
    print(f"  {name}: {matches or 'NONE'}")
