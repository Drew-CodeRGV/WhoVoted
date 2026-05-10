#!/usr/bin/env python3
"""Check if precinct boundary GeoJSON/shapefiles exist on the server."""
import os, json, glob

# Check common locations
paths = [
    '/opt/whovoted/public/data/precincts.json',
    '/opt/whovoted/public/data/hidalgo_precincts.json',
    '/opt/whovoted/public/data/precinct_boundaries.json',
    '/opt/whovoted/public/data/voting_precincts.json',
    '/opt/whovoted/data/hidalgo_precincts.geojson',
    '/opt/whovoted/data/precincts.geojson',
]
for p in paths:
    if os.path.exists(p):
        print(f"FOUND: {p} ({os.path.getsize(p)/1024:.0f} KB)")

# Search for anything precinct/vtd related
for d in ['/opt/whovoted/public/data', '/opt/whovoted/data', '/opt/whovoted/data/district_reference']:
    if os.path.exists(d):
        files = [f for f in os.listdir(d) if 'precinct' in f.lower() or 'vtd' in f.lower() or 'pct' in f.lower()]
        if files:
            print(f"\nIn {d}:")
            for f in files:
                size = os.path.getsize(os.path.join(d, f))
                print(f"  {f} ({size/1024:.0f} KB)")

# Check for shapefiles anywhere
shps = glob.glob('/opt/whovoted/**/*precinct*', recursive=True) + glob.glob('/opt/whovoted/**/*vtd*', recursive=True)
if shps:
    print(f"\nShapefiles/related:")
    for s in shps[:20]:
        print(f"  {s}")

# Check if we can download from Hidalgo County GIS
print("\n\nNote: Hidalgo County precinct boundaries can be downloaded from:")
print("  https://gis.hidalgocounty.us/arcgis/rest/services")
print("  or Census TIGER/Line VTD files")
