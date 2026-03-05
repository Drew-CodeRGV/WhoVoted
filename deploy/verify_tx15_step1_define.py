#!/usr/bin/env python3
"""
STEP 1: Define TX-15 Congressional District
Download and verify the official district boundaries.
"""

import json
import requests
import sys

def main():
    print("=" * 80)
    print("STEP 1: DEFINE TX-15 CONGRESSIONAL DISTRICT")
    print("=" * 80)
    
    # TX-15 is in South Texas, covering parts of:
    # - Hidalgo County (partial - southern/eastern portions)
    # - Brooks County (full)
    # - Jim Hogg County (full)
    # - Starr County (full)
    # - Willacy County (partial)
    # - Kenedy County (full)
    
    print("\nTX-15 Official Definition (2023 redistricting):")
    print("-" * 80)
    print("Counties (full or partial):")
    print("  - Hidalgo County (PARTIAL - eastern/southern portions)")
    print("  - Brooks County (FULL)")
    print("  - Jim Hogg County (FULL)")
    print("  - Starr County (FULL)")
    print("  - Willacy County (PARTIAL)")
    print("  - Kenedy County (FULL)")
    print("\nNOTE: Travis County is NOT in TX-15!")
    print("      Travis County is in TX-21, TX-25, TX-35, TX-37")
    
    # Check if we have the GeoJSON file
    import os
    geojson_path = 'data/tx_congressional_2023.geojson'
    
    if os.path.exists(geojson_path):
        print(f"\n✓ Found district boundaries file: {geojson_path}")
        
        with open(geojson_path, 'r') as f:
            data = json.load(f)
        
        # Find TX-15
        tx15 = None
        for feature in data.get('features', []):
            props = feature.get('properties', {})
            if props.get('DISTRICT') == '15' or props.get('CD') == '15':
                tx15 = feature
                break
        
        if tx15:
            print("✓ Found TX-15 in GeoJSON file")
            props = tx15.get('properties', {})
            print(f"\nTX-15 Properties:")
            for key, value in props.items():
                print(f"  {key}: {value}")
        else:
            print("✗ TX-15 not found in GeoJSON file")
    else:
        print(f"\n✗ District boundaries file not found: {geojson_path}")
        print("\nTo download:")
        print("  1. Visit: https://www.census.gov/cgi-bin/geo/shapefiles/index.php")
        print("  2. Select: Congressional Districts")
        print("  3. Select: Texas")
        print("  4. Download and convert to GeoJSON")
    
    print("\n" + "=" * 80)
    print("NEXT STEP: Run verify_tx15_step2_counties.py")
    print("=" * 80)

if __name__ == '__main__':
    main()
