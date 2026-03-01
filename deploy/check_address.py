#!/usr/bin/env python3
import sqlite3, json
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT vuid, firstname, lastname, address, city, lat, lng, geocoded, current_party FROM voters WHERE address LIKE '%109 E HOUSTON%'").fetchall()
for r in rows:
    print(json.dumps(dict(r)))

# Also check what's in the GeoJSON for the current dataset
import os, glob
geojson_files = glob.glob('/opt/whovoted/public/data/*.json')
for f in sorted(geojson_files):
    if 'geojson' in os.path.basename(f).lower() or ('2026' in f and 'meta' not in f):
        print(f"\n--- {f} ---")
        with open(f) as fh:
            data = json.load(fh)
            if 'features' in data:
                count = 0
                for feat in data['features']:
                    addr = feat.get('properties', {}).get('address', '')
                    if '109 E HOUSTON' in addr.upper():
                        count += 1
                        print(json.dumps(feat['properties']))
                if count == 0:
                    print("(no 109 E HOUSTON found)")
