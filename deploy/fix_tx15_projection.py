#!/usr/bin/env python3
"""Fix TX-15 projection using correct Lambert Conformal Conic parameters."""
import json
import sys

try:
    from pyproj import Transformer, CRS
except ImportError:
    import os
    os.system(f"{sys.executable} -m pip install pyproj")
    from pyproj import Transformer, CRS

# The .prj file says: NAD_1983_Lambert_Conformal_Conic
# This is a custom Texas projection, not a standard EPSG

# Define the projection from the .prj file parameters
# Standard Texas Lambert Conformal Conic parameters
proj_string = """
+proj=lcc 
+lat_1=27.5 
+lat_2=35 
+lat_0=18 
+lon_0=-100 
+x_0=1500000 
+y_0=6000000 
+ellps=GRS80 
+units=m 
+no_defs
"""

input_file = sys.argv[1] if len(sys.argv) > 1 else '../public/d15/tx15_boundary.json'

print(f"Reading {input_file}...")
with open(input_file) as f:
    data = json.load(f)

feat = data['features'][0]
coords = feat['geometry']['coordinates'][0]

print(f"Original sample: {coords[0]}")
print(f"Original bounds: x={min(c[0] for c in coords):.0f} to {max(c[0] for c in coords):.0f}")
print(f"                 y={min(c[1] for c in coords):.0f} to {max(c[1] for c in coords):.0f}")

# Try the custom projection
try:
    crs_from = CRS.from_proj4(proj_string)
    transformer = Transformer.from_crs(crs_from, "EPSG:4326", always_xy=True)
    
    def reproject(coords_list):
        if isinstance(coords_list[0], (int, float)):
            return list(transformer.transform(coords_list[0], coords_list[1]))
        return [reproject(c) for c in coords_list]
    
    feat['geometry']['coordinates'] = [reproject(coords)]
    
    new_coords = feat['geometry']['coordinates'][0]
    lngs = [c[0] for c in new_coords]
    lats = [c[1] for c in new_coords]
    
    print(f"\nReprojected sample: {new_coords[0]}")
    print(f"Reprojected bounds: lng={min(lngs):.4f} to {max(lngs):.4f}")
    print(f"                    lat={min(lats):.4f} to {max(lats):.4f}")
    
    if -107 < min(lngs) and max(lngs) < -93 and 25 < min(lats) and max(lats) < 37:
        print("✓ Coordinates look good for Texas!")
        
        with open(input_file, 'w') as f:
            json.dump(data, f)
        
        print(f"✓ Saved corrected file")
    else:
        print("✗ Coordinates still outside Texas range")
        
except Exception as e:
    print(f"Error: {e}")
