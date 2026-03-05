#!/usr/bin/env python3
"""
STEP 2: ACQUIRE - Download official district boundary data
Get authoritative shapefiles/GeoJSON for all district types.
"""

import os
import requests
import json
import zipfile
import subprocess

def main():
    print("=" * 80)
    print("ACQUIRE OFFICIAL DISTRICT BOUNDARIES")
    print("=" * 80)
    
    data_dir = 'data/districts'
    os.makedirs(data_dir, exist_ok=True)
    
    print("\n" + "=" * 80)
    print("1. CONGRESSIONAL DISTRICTS (2023 Redistricting)")
    print("=" * 80)
    
    # Texas Legislative Council has the official boundaries
    print("\nOfficial Source: Texas Legislative Council")
    print("URL: https://data.capitol.texas.gov/")
    
    cd_file = f'{data_dir}/tx_congressional_2023.geojson'
    if os.path.exists(cd_file):
        print(f"✓ Already have: {cd_file}")
        with open(cd_file, 'r') as f:
            data = json.load(f)
        print(f"  Features: {len(data.get('features', []))}")
    else:
        print(f"✗ Need to download: {cd_file}")
        print("\nManual download steps:")
        print("  1. Visit: https://data.capitol.texas.gov/")
        print("  2. Search for: 'Congressional Districts 2023'")
        print("  3. Download GeoJSON format")
        print(f"  4. Save to: {cd_file}")
        print("\nAlternative - Census Bureau:")
        print("  1. Visit: https://www.census.gov/cgi-bin/geo/shapefiles/index.php")
        print("  2. Select: Congressional Districts")
        print("  3. Select: Texas")
        print("  4. Convert shapefile to GeoJSON")
    
    print("\n" + "=" * 80)
    print("2. STATE HOUSE DISTRICTS (2023 Redistricting)")
    print("=" * 80)
    
    sh_file = f'{data_dir}/tx_state_house_2023.geojson'
    if os.path.exists(sh_file):
        print(f"✓ Already have: {sh_file}")
        with open(sh_file, 'r') as f:
            data = json.load(f)
        print(f"  Features: {len(data.get('features', []))}")
    else:
        print(f"✗ Need to download: {sh_file}")
        print("\nManual download steps:")
        print("  1. Visit: https://data.capitol.texas.gov/")
        print("  2. Search for: 'State House Districts 2023'")
        print("  3. Download GeoJSON format")
        print(f"  4. Save to: {sh_file}")
    
    print("\n" + "=" * 80)
    print("3. COMMISSIONER PRECINCTS (County-Specific)")
    print("=" * 80)
    
    print("\nCommissioner precincts are county-specific.")
    print("Need to download for each county separately.")
    
    # Check what we have
    counties_with_comm = []
    for county in ['Hidalgo', 'Cameron', 'Starr', 'Willacy']:
        comm_file = f'{data_dir}/{county.lower()}_commissioner_precincts.geojson'
        if os.path.exists(comm_file):
            print(f"✓ {county} County: {comm_file}")
            counties_with_comm.append(county)
        else:
            print(f"✗ {county} County: Need {comm_file}")
    
    if not counties_with_comm:
        print("\nSources for commissioner precinct boundaries:")
        print("  - County GIS departments")
        print("  - County election offices")
        print("  - Texas Secretary of State")
        print("  - Local open data portals")
    
    print("\n" + "=" * 80)
    print("4. PRECINCT BOUNDARIES (Voting Precincts)")
    print("=" * 80)
    
    print("\nVoting precinct boundaries are also county-specific.")
    
    counties_with_precincts = []
    for county in ['Hidalgo', 'Cameron', 'Starr', 'Willacy']:
        precinct_file = f'{data_dir}/{county.lower()}_voting_precincts.geojson'
        if os.path.exists(precinct_file):
            print(f"✓ {county} County: {precinct_file}")
            counties_with_precincts.append(county)
        else:
            print(f"✗ {county} County: Need {precinct_file}")
    
    print("\n" + "=" * 80)
    print("5. VERIFY EXISTING FILES")
    print("=" * 80)
    
    # Check if we have the files we're currently using
    current_files = [
        'data/tx_congressional_2023.geojson',
        'data/tx_state_house_2023.geojson',
        'data/hidalgo_precincts.geojson',
        'data/cameron_precincts.geojson'
    ]
    
    print("\nChecking current data files:")
    for filepath in current_files:
        if os.path.exists(filepath):
            print(f"✓ {filepath}")
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)
                features = data.get('features', [])
                print(f"  Features: {len(features)}")
                if features:
                    props = features[0].get('properties', {})
                    print(f"  Sample properties: {list(props.keys())[:5]}")
            except Exception as e:
                print(f"  ✗ Error reading file: {e}")
        else:
            print(f"✗ {filepath} - NOT FOUND")
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    required_files = [
        ('Congressional Districts', cd_file),
        ('State House Districts', sh_file),
    ]
    
    missing = [name for name, path in required_files if not os.path.exists(path)]
    
    if missing:
        print(f"\n✗ Missing {len(missing)} required files:")
        for name in missing:
            print(f"  - {name}")
        print("\nCannot proceed to Step 3 until these are downloaded.")
    else:
        print("\n✓ All required boundary files are present")
        print("\nReady for Step 3: python3 verify_districts_step3_validate.py")

if __name__ == '__main__':
    main()
