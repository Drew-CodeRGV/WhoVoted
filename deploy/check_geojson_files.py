#!/usr/bin/env python3
import os, json, glob
for f in sorted(glob.glob("/opt/whovoted/public/data/map_data_*2026*.json")):
    with open(f) as fh:
        data = json.load(fh)
    features = data.get("features", [])
    geocoded = sum(1 for feat in features if feat.get("geometry") is not None)
    print(f"{os.path.basename(f)}: {len(features)} features, {geocoded} geocoded, {len(features)-geocoded} ungeocoded")
