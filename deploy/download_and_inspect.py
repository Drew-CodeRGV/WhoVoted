#!/usr/bin/env python3
import shapefile
import urllib.request
import zipfile
import os

url = 'https://data.capitol.texas.gov/dataset/748c952b-e926-4f44-8d01-a738884b3ec8/resource/5712ebe1-d777-4d4a-b836-0534e17bca01/download/planc2333.zip'
extract_dir = '/tmp/planc2333'
os.makedirs(extract_dir, exist_ok=True)

zip_path = os.path.join(extract_dir, 'download.zip')
req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (compatible)'})
with urllib.request.urlopen(req, timeout=60) as resp:
    with open(zip_path, 'wb') as f:
        f.write(resp.read())

with zipfile.ZipFile(zip_path, 'r') as z:
    z.extractall(extract_dir)

# Find .shp
shp_path = None
for root, dirs, files in os.walk(extract_dir):
    for f in files:
        fp = os.path.join(root, f)
        print(f"  {fp}")
        if f.lower().endswith('.shp'):
            shp_path = fp

if not shp_path:
    print("No .shp found")
    exit(1)

sf = shapefile.Reader(shp_path)
print(f"\nFields: {[f[0] for f in sf.fields[1:]]}")
print(f"Records: {len(sf)}")
print(f"Bounding box: {sf.bbox}")

# Check projection
prj_path = shp_path.replace('.shp', '.prj')
if os.path.exists(prj_path):
    with open(prj_path) as f:
        print(f"Projection: {f.read()[:300]}")

# Show first 3 records with sample coords
for i, sr in enumerate(sf.shapeRecords()[:3]):
    props = {}
    for j, field in enumerate(sf.fields[1:]):
        props[field[0]] = sr.record[j]
    geom = sr.shape.__geo_interface__
    if geom['type'] == 'Polygon':
        sample = geom['coordinates'][0][:3]
    elif geom['type'] == 'MultiPolygon':
        sample = geom['coordinates'][0][0][:3]
    else:
        sample = 'unknown'
    print(f"\nDistrict {i}: {props}")
    print(f"  Type: {geom['type']}, Sample coords: {sample}")
