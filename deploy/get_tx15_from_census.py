#!/usr/bin/env python3
"""Get TX-15 from Census TIGERweb API (already in WGS84)."""
import json
import urllib.request
import sys

# Census TIGERweb REST API for 119th Congressional Districts
# This returns GeoJSON in WGS84 (EPSG:4326) - no reprojection needed!
base_url = "https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/8/query"

params = {
    "where": "STATE='48' AND BASENAME='15'",  # Texas, District 15
    "outFields": "*",
    "returnGeometry": "true",
    "f": "geojson",
    "outSR": "4326"  # WGS84
}

import urllib.parse
query_string = urllib.parse.urlencode(params)
url = f"{base_url}?{query_string}"

print(f"Fetching TX-15 from Census TIGERweb...")
print(f"URL: {url[:100]}...")

req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read().decode())

if "features" in data and len(data["features"]) > 0:
    feat = data["features"][0]
    
    # Update properties
    feat["properties"] = {
        "district_type": "congressional",
        "district_id": "TX-15",
        "district_name": "TX-15 Congressional District",
        "color": "#3b82f6",
        "plan": "119th Congress"
    }
    
    # Calculate bounds
    coords = feat["geometry"]["coordinates"]
    if feat["geometry"]["type"] == "Polygon":
        all_coords = coords[0]
    else:
        all_coords = [c for ring in coords[0] for c in ring]
    
    lngs = [c[0] for c in all_coords]
    lats = [c[1] for c in all_coords]
    
    print(f"\nTX-15 bounds:")
    print(f"  Longitude: {min(lngs):.4f} to {max(lngs):.4f}")
    print(f"  Latitude: {min(lats):.4f} to {max(lats):.4f}")
    print(f"  Center: [{(min(lngs)+max(lngs))/2:.4f}, {(min(lats)+max(lats))/2:.4f}]")
    
    # Save
    output_path = sys.argv[1] if len(sys.argv) > 1 else '../public/d15/tx15_boundary.json'
    with open(output_path, 'w') as f:
        json.dump(data, f)
    
    print(f"\n✓ Saved TX-15 boundary to {output_path}")
    print(f"✓ This is the CURRENT 119th Congress boundary (2023-2025)")
    print(f"  Note: PlanC2333 (2026+) may have different boundaries")
else:
    print("✗ No features found")
    print(f"Response: {json.dumps(data, indent=2)[:500]}")
