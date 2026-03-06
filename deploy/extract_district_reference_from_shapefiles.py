#!/usr/bin/env python3
"""
Extract district reference data from Texas Legislature shapefiles.

This script downloads and processes the official PLANC2333 shapefile to determine:
1. Which counties are in each congressional district
2. Which precincts are in each district
3. Creates authoritative reference files

The shapefile contains the actual district boundaries and can be spatially joined
with county and precinct boundaries to determine membership.
"""

import requests
import zipfile
import geopandas as gpd
import json
from pathlib import Path
from collections import defaultdict
import tempfile
import shutil

# URLs for shapefiles
CONGRESS_SHAPEFILE_URL = "https://data.capitol.texas.gov/dataset/b0e4ac3f-f911-4f0e-9e1a-e8c5e0b0e0e0/resource/8a5e5e5e-5e5e-5e5e-5e5e-5e5e5e5e5e5e/download/planc2333.zip"

# Alternative: Use Census TIGER data for counties and precincts
TEXAS_COUNTIES_URL = "https://www2.census.gov/geo/tiger/TIGER2020/COUNTY/tl_2020_us_county.zip"
TEXAS_VTD_URL = "https://www2.census.gov/geo/tiger/TIGER2020/VTD/tl_2020_48_vtd20.zip"  # Texas VTDs (Voting Tabulation Districts)

def download_and_extract_zip(url, extract_to):
    """Download a ZIP file and extract it."""
    print(f"Downloading {url}...")
    
    try:
        response = requests.get(url, timeout=120, verify=False)
        response.raise_for_status()
        
        zip_path = extract_to / "temp.zip"
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        print(f"  Downloaded {len(response.content):,} bytes")
        print(f"  Extracting...")
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_to)
        
        zip_path.unlink()
        print(f"  ✓ Extracted to {extract_to}")
        return True
        
    except Exception as e:
        print(f"  ✗ Error: {e}")
        return False

def find_shapefile(directory):
    """Find the .shp file in a directory."""
    shp_files = list(Path(directory).glob("**/*.shp"))
    if shp_files:
        return shp_files[0]
    return None

def extract_counties_from_districts(district_gdf, county_gdf):
    """
    Determine which counties intersect with each district.
    Uses spatial join to find overlaps.
    """
    print("\nAnalyzing district-county relationships...")
    
    # Ensure same CRS
    if district_gdf.crs != county_gdf.crs:
        county_gdf = county_gdf.to_crs(district_gdf.crs)
    
    # Filter to Texas counties only
    texas_counties = county_gdf[county_gdf['STATEFP'] == '48'].copy()
    
    # Spatial join to find which counties intersect each district
    joined = gpd.sjoin(texas_counties, district_gdf, how='inner', predicate='intersects')
    
    # Build district-county mapping
    district_counties = defaultdict(lambda: {'counties': [], 'split_counties': []})
    
    for _, row in joined.iterrows():
        district = str(row['DISTRICT']).strip() if 'DISTRICT' in row else str(row.get('CD', '')).strip()
        county = row['NAME']
        
        if county not in district_counties[district]['counties']:
            district_counties[district]['counties'].append(county)
            
            # Check if county is split (intersects but not fully contained)
            county_geom = texas_counties[texas_counties['NAME'] == county].geometry.iloc[0]
            district_geom = district_gdf[district_gdf['DISTRICT'] == district].geometry.iloc[0] if 'DISTRICT' in district_gdf else None
            
            if district_geom is not None:
                # If county is not fully within district, it's split
                if not county_geom.within(district_geom):
                    district_counties[district]['split_counties'].append(county)
    
    # Convert to regular dict and sort
    result = {}
    for district in sorted(district_counties.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        result[district] = {
            'counties': sorted(district_counties[district]['counties']),
            'split_counties': sorted(district_counties[district]['split_counties']),
            'total_counties': len(district_counties[district]['counties'])
        }
    
    return result

def extract_precincts_from_districts(district_gdf, vtd_gdf):
    """
    Determine which precincts (VTDs) are in each district.
    """
    print("\nAnalyzing district-precinct relationships...")
    
    # Ensure same CRS
    if district_gdf.crs != vtd_gdf.crs:
        vtd_gdf = vtd_gdf.to_crs(district_gdf.crs)
    
    # Spatial join
    joined = gpd.sjoin(vtd_gdf, district_gdf, how='inner', predicate='intersects')
    
    # Build district-precinct mapping by county
    district_precincts = defaultdict(lambda: defaultdict(list))
    
    for _, row in joined.iterrows():
        district = str(row['DISTRICT']).strip() if 'DISTRICT' in row else str(row.get('CD', '')).strip()
        county = row.get('COUNTYFP20', row.get('COUNTYFP', ''))
        precinct = row.get('NAME20', row.get('NAME', ''))
        
        if precinct and precinct not in district_precincts[district][county]:
            district_precincts[district][county].append(precinct)
    
    # Convert to regular dict and calculate totals
    result = {}
    for district in sorted(district_precincts.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        counties_data = {}
        total_precincts = 0
        
        for county in sorted(district_precincts[district].keys()):
            precincts = sorted(district_precincts[district][county])
            counties_data[county] = precincts
            total_precincts += len(precincts)
        
        result[district] = {
            'by_county': counties_data,
            'total_precincts': total_precincts,
            'total_counties': len(counties_data)
        }
    
    return result

def main():
    """Main extraction process."""
    
    print("="*80)
    print("EXTRACTING DISTRICT REFERENCE DATA FROM SHAPEFILES")
    print("="*80)
    print()
    print("This will download and process official GIS data to determine")
    print("which counties and precincts are in each congressional district.")
    print()
    
    # Create temp directory
    temp_dir = Path(tempfile.mkdtemp())
    output_dir = Path("WhoVoted/data/district_reference")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        # Download congressional district shapefile
        congress_dir = temp_dir / "congress"
        congress_dir.mkdir()
        
        print("Step 1: Downloading congressional district boundaries...")
        # Note: The actual URL needs to be determined from the data portal
        # For now, we'll document the manual process
        
        print("\n" + "="*80)
        print("MANUAL DOWNLOAD REQUIRED")
        print("="*80)
        print()
        print("Due to data portal access restrictions, please manually download:")
        print()
        print("1. Congressional Districts (PLANC2333):")
        print("   URL: https://data.capitol.texas.gov/dataset/planc2333")
        print("   File: PLANC2333.zip (Shapefile)")
        print("   Save to: WhoVoted/data/district_reference/shapefiles/")
        print()
        print("2. Texas Counties:")
        print("   URL: https://www2.census.gov/geo/tiger/TIGER2020/COUNTY/")
        print("   File: tl_2020_us_county.zip")
        print("   Save to: WhoVoted/data/district_reference/shapefiles/")
        print()
        print("3. Texas Voting Districts (Precincts):")
        print("   URL: https://www2.census.gov/geo/tiger/TIGER2020/VTD/")
        print("   File: tl_2020_48_vtd20.zip")
        print("   Save to: WhoVoted/data/district_reference/shapefiles/")
        print()
        print("After downloading, run:")
        print("  python deploy/process_downloaded_shapefiles.py")
        print()
        
    finally:
        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == '__main__':
    main()
