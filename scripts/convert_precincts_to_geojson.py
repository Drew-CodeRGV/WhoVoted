#!/usr/bin/env python3
"""
Convert Texas VTD Shapefile to GeoJSON for specific counties

This script downloads and converts the official Texas precinct boundaries
from the Capitol Data Portal to GeoJSON format.

Usage:
    python convert_precincts_to_geojson.py --county 215 --output precinct_boundaries.json

Requirements:
    pip install geopandas requests
"""

import argparse
import json
import sys
from pathlib import Path
import zipfile
import tempfile
import shutil

try:
    import geopandas as gpd
    import requests
except ImportError:
    print("Error: Required packages not installed.")
    print("Please run: pip install geopandas requests")
    sys.exit(1)

# Texas county FIPS codes
COUNTY_FIPS = {
    'hidalgo': 215,
    'cameron': 61,
    'starr': 427,
    'willacy': 489,
}

# Official data source
VTD_SHAPEFILE_URL = 'https://data.capitol.texas.gov/dataset/b3554821-d3d1-425c-9d2a-88e7b15c1a1e/resource/d7a5f93e-e6f8-4c1e-9a5e-3e0c4e5e5e5e/download/vtds_24pg.zip'


def download_shapefile(url, temp_dir):
    """Download and extract the VTD shapefile"""
    print(f"Downloading shapefile from {url}...")
    
    response = requests.get(url, stream=True)
    response.raise_for_status()
    
    zip_path = temp_dir / 'vtds.zip'
    with open(zip_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print("Extracting shapefile...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
    
    # Find the .shp file
    shp_files = list(temp_dir.glob('*.shp'))
    if not shp_files:
        raise FileNotFoundError("No .shp file found in the downloaded archive")
    
    return shp_files[0]


def convert_to_geojson(shapefile_path, county_fips, output_path, simplify=True):
    """Convert shapefile to GeoJSON for specific county"""
    print(f"Reading shapefile: {shapefile_path}")
    gdf = gpd.read_file(shapefile_path)
    
    print(f"Total precincts in Texas: {len(gdf)}")
    
    # Filter for specific county
    county_gdf = gdf[gdf['CNTY'] == county_fips].copy()
    print(f"Precincts in selected county: {len(county_gdf)}")
    
    if len(county_gdf) == 0:
        print(f"Warning: No precincts found for county FIPS code {county_fips}")
        return
    
    # Convert to WGS84 (EPSG:4326) for web mapping
    if county_gdf.crs != 'EPSG:4326':
        print("Converting to WGS84 (EPSG:4326)...")
        county_gdf = county_gdf.to_crs('EPSG:4326')
    
    # Simplify geometries to reduce file size (optional)
    if simplify:
        print("Simplifying geometries...")
        county_gdf['geometry'] = county_gdf['geometry'].simplify(tolerance=0.0001, preserve_topology=True)
    
    # Rename fields for clarity
    county_gdf = county_gdf.rename(columns={
        'VTD': 'precinct_id',
        'VTDKEY': 'vtd_key',
        'CNTYVTD': 'county_vtd'
    })
    
    # Add placeholder turnout data (to be filled in later)
    county_gdf['precinct'] = 'Precinct ' + county_gdf['precinct_id'].astype(str)
    county_gdf['total_voters'] = 0
    county_gdf['voted_count'] = 0
    county_gdf['turnout_percentage'] = 0.0
    
    # Select only needed columns
    columns_to_keep = ['precinct_id', 'precinct', 'vtd_key', 'county_vtd', 
                       'total_voters', 'voted_count', 'turnout_percentage', 'geometry']
    county_gdf = county_gdf[columns_to_keep]
    
    # Save as GeoJSON
    print(f"Saving to {output_path}...")
    county_gdf.to_file(output_path, driver='GeoJSON')
    
    # Pretty print the JSON
    with open(output_path, 'r') as f:
        data = json.load(f)
    
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✓ Successfully created {output_path}")
    print(f"  - {len(county_gdf)} precincts")
    print(f"  - File size: {Path(output_path).stat().st_size / 1024:.1f} KB")


def main():
    parser = argparse.ArgumentParser(
        description='Convert Texas VTD shapefile to GeoJSON for specific counties'
    )
    parser.add_argument(
        '--county',
        type=str,
        default='hidalgo',
        help='County name or FIPS code (default: hidalgo)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='../public/data/precinct_boundaries.json',
        help='Output GeoJSON file path'
    )
    parser.add_argument(
        '--shapefile',
        type=str,
        help='Path to local shapefile (skip download if provided)'
    )
    parser.add_argument(
        '--no-simplify',
        action='store_true',
        help='Do not simplify geometries'
    )
    
    args = parser.parse_args()
    
    # Determine county FIPS code
    if args.county.isdigit():
        county_fips = int(args.county)
    else:
        county_name = args.county.lower()
        if county_name not in COUNTY_FIPS:
            print(f"Error: Unknown county '{args.county}'")
            print(f"Available counties: {', '.join(COUNTY_FIPS.keys())}")
            print("Or provide a FIPS code directly")
            sys.exit(1)
        county_fips = COUNTY_FIPS[county_name]
    
    print(f"Processing county FIPS code: {county_fips}")
    
    # Create output directory if needed
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use local shapefile or download
    if args.shapefile:
        shapefile_path = Path(args.shapefile)
        if not shapefile_path.exists():
            print(f"Error: Shapefile not found: {shapefile_path}")
            sys.exit(1)
        convert_to_geojson(shapefile_path, county_fips, output_path, not args.no_simplify)
    else:
        # Download and process
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            try:
                shapefile_path = download_shapefile(VTD_SHAPEFILE_URL, temp_path)
                convert_to_geojson(shapefile_path, county_fips, output_path, not args.no_simplify)
            except Exception as e:
                print(f"Error: {e}")
                print("\nIf download fails, manually download from:")
                print("https://data.capitol.texas.gov/dataset/vtds")
                print("Then run with --shapefile option")
                sys.exit(1)


if __name__ == '__main__':
    main()
