#!/usr/bin/env python3
import shapefile
import os

shp_dir = '/tmp/tmp4q8d3vu9/PLANC2333'
# Find .shp
for root, dirs, files in os.walk('/tmp'):
    for f in files:
        if f == 'PLANC2333.shp':
            shp_dir = root
            break

shp_path = os.path.join(shp_dir, 'PLANC2333.shp')
if not os.path.exists(shp_path):
    # Try to re-extract
    print("Shapefile not found, listing /tmp contents:")
    for root, dirs, files in os.walk('/tmp'):
        for f in files:
            if 'PLANC' in f:
                print(f"  {os.path.join(root, f)}")
    exit(1)

sf = shapefile.Reader(shp_path)
print("Fields:", [f[0] for f in sf.fields[1:]])
print(f"Total records: {len(sf)}")
print(f"Bounding box: {sf.bbox}")

# Check first few records
for i, sr in enumerate(sf.shapeRecords()[:5]):
    props = {}
    for j, field in enumerate(sf.fields[1:]):
        props[field[0]] = sr.record[j]
    geom = sr.shape.__geo_interface__
    coords = geom['coordinates']
    if geom['type'] == 'Polygon':
        sample = coords[0][:3]
    elif geom['type'] == 'MultiPolygon':
        sample = coords[0][0][:3]
    else:
        sample = str(coords)[:200]
    print(f"\nRecord {i}: {props}")
    print(f"  Geometry type: {geom['type']}")
    print(f"  Sample coords: {sample}")

# Check .prj file
prj_path = shp_path.replace('.shp', '.prj')
if os.path.exists(prj_path):
    with open(prj_path) as f:
        print(f"\nProjection (.prj): {f.read()[:500]}")
