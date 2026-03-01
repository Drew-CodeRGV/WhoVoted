#!/usr/bin/env python3
"""
Create Hidalgo County Commissioner Precinct boundaries and add to districts.json.

Uses approximate boundaries based on official county descriptions:
- Pct 1: Eastern (Mercedes to Alamo, Hargill south to Progresso Lakes)
- Pct 2: Southern (Hidalgo, McAllen, Pharr, San Juan, south of Alamo)
- Pct 3: Western (Cuervitas to Cipres, east to ~FM1017, part of Hidalgo city)
- Pct 4: Northern (north of San Manuel to Brooks County, parts of McAllen, east to Hargill)

These are approximate boundaries derived from the county's official precinct
descriptions at hidalgocounty.us/487/Maps and known city locations.
"""
import json
import sys

COLORS = {
    '1': '#e74c3c',  # Red
    '2': '#3498db',  # Blue
    '3': '#2ecc71',  # Green
    '4': '#f39c12',  # Orange
}

# Hidalgo County approximate bounding box
# West: ~-98.585, East: ~-97.585, South: ~26.05, North: ~26.80
COUNTY_W = -98.585
COUNTY_E = -97.585
COUNTY_S = 26.05
COUNTY_N = 26.80

# Key reference points (lng, lat):
# McAllen center: -98.23, 26.20
# Pharr: -98.18, 26.19
# San Juan: -98.155, 26.19
# Alamo: -98.12, 26.18
# Mercedes: -97.91, 26.15
# Weslaco: -97.99, 26.16
# Edinburg: -98.16, 26.30
# Mission: -98.33, 26.22
# Hidalgo city: -98.26, 26.10
# Progresso Lakes: -97.96, 26.06
# Hargill: -97.89, 26.44
# San Manuel: -98.13, 26.56
# Sullivan City: -98.56, 26.28
# La Joya: -98.48, 26.25

# The dividing lines between precincts are approximate.
# Based on the descriptions:
#
# The county is roughly divided into 4 quadrants:
# - A north-south line roughly along ~-98.12 (Alamo/Edinburg area) separates East from West
# - An east-west line roughly along ~26.30 (Edinburg latitude) separates North from South
#
# But the actual boundaries are more complex. Here's the approximation:
#
# Pct 1 (East): East of ~-98.12, south of ~26.44 (Hargill)
# Pct 2 (South): South of ~26.25, between ~-98.35 and ~-98.12
# Pct 3 (West): West of ~-98.35, south of ~26.50
# Pct 4 (North): North of ~26.35, from ~-98.35 east to ~-97.89

# More refined boundaries based on city locations and descriptions:

def create_precinct_boundaries():
    """Create approximate commissioner precinct polygons."""
    
    # Precinct 1 - Eastern Hidalgo County
    # Mercedes west to Alamo, Hargill on northern border south to Progresso Lakes
    pct1 = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-98.12, 26.44],   # Hargill area (NW corner of Pct 1)
                [-97.585, 26.44],  # NE - county east border at Hargill latitude
                [-97.585, 26.05],  # SE - county SE corner
                [-97.96, 26.05],   # S - near Progresso Lakes
                [-97.96, 26.12],   # Progresso Lakes area
                [-98.00, 26.15],   # Near Weslaco south
                [-98.05, 26.18],   # Between Weslaco and Alamo
                [-98.12, 26.20],   # Alamo area
                [-98.12, 26.44],   # Back to Hargill
            ]]
        },
        "properties": {
            "district_type": "commissioner",
            "district_id": "CPct-1",
            "district_name": "Commissioner Precinct 1",
            "color": COLORS['1'],
            "description": "Eastern Hidalgo County: Mercedes to Alamo, Hargill to Progresso Lakes"
        }
    }
    
    # Precinct 2 - Southern Hidalgo County
    # Hidalgo, McAllen, Pharr, San Juan, south of Alamo
    pct2 = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-98.35, 26.25],   # NW - west of McAllen
                [-98.12, 26.20],   # NE - Alamo area
                [-98.05, 26.18],   # East of Alamo
                [-98.00, 26.15],   # Near Weslaco south
                [-97.96, 26.12],   # Progresso Lakes area
                [-97.96, 26.05],   # SE - near Progresso Lakes at border
                [-98.35, 26.05],   # SW - county south border
                [-98.35, 26.25],   # Back to NW
            ]]
        },
        "properties": {
            "district_type": "commissioner",
            "district_id": "CPct-2",
            "district_name": "Commissioner Precinct 2",
            "color": COLORS['2'],
            "description": "Southern Hidalgo County: Hidalgo, McAllen, Pharr, San Juan"
        }
    }
    
    # Precinct 3 - Western Hidalgo County
    # Cuervitas at western border, north to Cipres, east ~20mi of FM1017, part of Hidalgo city
    pct3 = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-98.585, 26.60],  # NW - county west border, north
                [-98.35, 26.60],   # NE corner
                [-98.35, 26.25],   # SE - meets Pct 2
                [-98.35, 26.05],   # S - county south border
                [-98.585, 26.05],  # SW - county SW corner
                [-98.585, 26.60],  # Back to NW
            ]]
        },
        "properties": {
            "district_type": "commissioner",
            "district_id": "CPct-3",
            "district_name": "Commissioner Precinct 3",
            "color": COLORS['3'],
            "description": "Western Hidalgo County: Mission, Sullivan City, La Joya"
        }
    }
    
    # Precinct 4 - Northern Hidalgo County
    # North of San Manuel to Brooks County, parts of McAllen, east to Hargill
    pct4 = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-98.585, 26.80],  # NW - county NW corner
                [-97.585, 26.80],  # NE - county NE corner
                [-97.585, 26.44],  # E - at Hargill latitude
                [-98.12, 26.44],   # Hargill area
                [-98.12, 26.20],   # South to Alamo/Edinburg
                [-98.35, 26.25],   # West to McAllen area
                [-98.35, 26.60],   # NW meets Pct 3
                [-98.585, 26.60],  # County west border
                [-98.585, 26.80],  # Back to NW
            ]]
        },
        "properties": {
            "district_type": "commissioner",
            "district_id": "CPct-4",
            "district_name": "Commissioner Precinct 4",
            "color": COLORS['4'],
            "description": "Northern Hidalgo County: Edinburg, north to Brooks County"
        }
    }
    
    return [pct1, pct2, pct3, pct4]


def main():
    output_dir = "/opt/whovoted/public/data" if len(sys.argv) < 2 else sys.argv[1]
    districts_path = f"{output_dir}/districts.json"
    
    # Load existing districts.json
    try:
        with open(districts_path) as f:
            districts = json.load(f)
    except Exception:
        districts = {"type": "FeatureCollection", "features": []}
    
    # Remove any existing commissioner features
    before = len(districts['features'])
    districts['features'] = [f for f in districts['features']
                             if f.get('properties', {}).get('district_type') != 'commissioner']
    removed = before - len(districts['features'])
    if removed:
        print(f"Removed {removed} existing commissioner features")
    
    # Add new commissioner precincts
    precincts = create_precinct_boundaries()
    districts['features'].extend(precincts)
    
    # Save
    with open(districts_path, 'w') as f:
        json.dump(districts, f)
    
    total = len(districts['features'])
    comm = len([f for f in districts['features'] if f['properties']['district_type'] == 'commissioner'])
    print(f"Added {comm} commissioner precincts to districts.json ({total} total features)")
    print(f"File size: {len(json.dumps(districts)) / 1024:.1f} KB")
    
    for p in precincts:
        props = p['properties']
        print(f"  {props['district_id']}: {props['district_name']} ({props['color']})")
        print(f"    {props['description']}")


if __name__ == "__main__":
    main()
