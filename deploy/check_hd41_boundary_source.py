#!/usr/bin/env python3
"""Check the current HD-41 boundary: source, accuracy, bounding box."""
import json

with open("/opt/whovoted/public/data/districts.json") as f:
    d = json.load(f)

hd41 = [feat for feat in d["features"] if feat["properties"].get("district_id") == "HD-41"]
if not hd41:
    print("HD-41 NOT FOUND in districts.json")
    exit(1)

props = hd41[0]["properties"]
geom = hd41[0]["geometry"]

print(f"Geometry type: {geom['type']}")
if geom['type'] == 'Polygon':
    coords = geom['coordinates'][0]
elif geom['type'] == 'MultiPolygon':
    coords = geom['coordinates'][0][0]
    print(f"  MultiPolygon with {len(geom['coordinates'])} parts")
else:
    coords = []

print(f"Vertices: {len(coords)}")
print(f"\nProperties:")
for k, v in sorted(props.items()):
    if v and str(v).strip():
        print(f"  {k}: {v}")

if coords:
    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    print(f"\nBounding box:")
    print(f"  Lat: {min(lats):.4f} to {max(lats):.4f}")
    print(f"  Lng: {min(lngs):.4f} to {max(lngs):.4f}")
    print(f"  Center: {(min(lats)+max(lats))/2:.4f}, {(min(lngs)+max(lngs))/2:.4f}")

# Check which TIGERweb layer it came from
print(f"\nSource: Census TIGERweb Legislative layer")
print(f"  LSY (Legislative Session Year): {props.get('LSY', 'unknown')}")
print(f"  GEOID: {props.get('GEOID', 'unknown')}")
print(f"  SLDL: {props.get('SLDL', 'unknown')}")
print(f"  FUNCSTAT: {props.get('FUNCSTAT', 'unknown')}")

# The issue: Census TIGER boundaries may be from 2022 redistricting
# but the ACTUAL current boundaries may differ if there was a court order
# or if the 2024 redistricting changed things
print(f"\nNOTE: If this boundary looks wrong, it may be because:")
print(f"  1. Census TIGER uses 2021 redistricting boundaries (PLANH2316)")
print(f"  2. The actual current boundary may have been updated by court order")
print(f"  3. The TLC (Texas Legislative Council) has the authoritative boundaries")
print(f"  4. TLC boundary URL: https://dvr.capitol.texas.gov/")
