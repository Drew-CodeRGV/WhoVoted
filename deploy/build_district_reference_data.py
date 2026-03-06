#!/usr/bin/env python3
"""
Build comprehensive district reference data from Texas Legislature official sources.

Downloads and parses:
- PLANC2333_r150.xls: Districts by County
- PLANC2333_r365_Prec24G.xls: Precincts in District by County  
- PLANC2333_r385.xls: ZIP Codes by District

This creates authoritative reference files showing what counties, precincts, and ZIP codes
are in each congressional district, regardless of whether we have voter data.
"""

import requests
import pandas as pd
import json
from pathlib import Path
from collections import defaultdict
import urllib3

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Base URL for Texas Legislature redistricting data
BASE_URL = "https://data.capitol.texas.gov/dataset/b0e4ac3f-f911-4f0e-9e1a-e8c5e0b0e0e0/resource"

# Files to download - these are the resource IDs from the data portal
FILES = {
    'counties': {
        'name': 'PLANC2333_r150.xls',
        'description': 'Districts by County',
        'output': 'district_counties.json'
    },
    'precincts': {
        'name': 'PLANC2333_r365_Prec24G.xls', 
        'description': 'Precincts in District by County',
        'output': 'district_precincts.json'
    },
    'zipcodes': {
        'name': 'PLANC2333_r385.xls',
        'description': 'ZIP Codes by District',
        'output': 'district_zipcodes.json'
    }
}

def download_file(filename):
    """Try multiple URL patterns to download the file."""
    
    # Try direct redistricting site
    urls = [
        f"https://redistricting.capitol.texas.gov/docs/plans/congress/PLANC2333/reports/{filename}",
        f"https://data.capitol.texas.gov/dataset/planc2333/resource/download/{filename}",
    ]
    
    for url in urls:
        try:
            print(f"  Trying: {url}")
            response = requests.get(url, timeout=30, allow_redirects=True, verify=False)
            if response.status_code == 200 and len(response.content) > 1000:
                print(f"  ✓ Downloaded {len(response.content):,} bytes")
                return response.content
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            continue
    
    return None

def parse_counties_file(content):
    """Parse the Districts by County XLS file."""
    temp_file = Path("temp_counties.xls")
    temp_file.write_bytes(content)
    
    try:
        df = pd.read_excel(temp_file, engine='xlrd')
        print(f"  Loaded {len(df)} rows, columns: {list(df.columns)}")
        
        # Build mapping
        district_data = defaultdict(lambda: {'counties': [], 'split_counties': []})
        
        for _, row in df.iterrows():
            # Try different possible column names
            district = None
            county = None
            is_split = False
            
            for col in df.columns:
                col_lower = str(col).lower()
                if 'district' in col_lower and district is None:
                    district = str(row[col]).strip()
                elif 'county' in col_lower and county is None:
                    county = str(row[col]).strip()
                elif 'split' in col_lower or 'partial' in col_lower:
                    is_split = str(row[col]).strip().upper() in ['Y', 'YES', 'TRUE', '1', 'SPLIT', 'PARTIAL']
            
            if district and county and district != 'nan' and county != 'nan':
                if county not in district_data[district]['counties']:
                    district_data[district]['counties'].append(county)
                    if is_split:
                        district_data[district]['split_counties'].append(county)
        
        # Convert to regular dict and sort
        result = {}
        for district in sorted(district_data.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            result[district] = {
                'counties': sorted(district_data[district]['counties']),
                'split_counties': sorted(district_data[district]['split_counties']),
                'total_counties': len(district_data[district]['counties'])
            }
        
        return result
        
    finally:
        temp_file.unlink(missing_ok=True)

def parse_precincts_file(content):
    """Parse the Precincts in District by County XLS file."""
    temp_file = Path("temp_precincts.xls")
    temp_file.write_bytes(content)
    
    try:
        df = pd.read_excel(temp_file, engine='xlrd')
        print(f"  Loaded {len(df)} rows, columns: {list(df.columns)}")
        
        # Build mapping
        district_data = defaultdict(lambda: defaultdict(list))
        
        for _, row in df.iterrows():
            district = None
            county = None
            precinct = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if 'district' in col_lower and district is None:
                    district = str(row[col]).strip()
                elif 'county' in col_lower and county is None:
                    county = str(row[col]).strip()
                elif 'precinct' in col_lower or 'pct' in col_lower:
                    precinct = str(row[col]).strip()
            
            if district and county and precinct and all(x != 'nan' for x in [district, county, precinct]):
                if precinct not in district_data[district][county]:
                    district_data[district][county].append(precinct)
        
        # Convert to regular dict and calculate totals
        result = {}
        for district in sorted(district_data.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            counties_data = {}
            total_precincts = 0
            
            for county in sorted(district_data[district].keys()):
                precincts = sorted(district_data[district][county])
                counties_data[county] = precincts
                total_precincts += len(precincts)
            
            result[district] = {
                'by_county': counties_data,
                'total_precincts': total_precincts,
                'total_counties': len(counties_data)
            }
        
        return result
        
    finally:
        temp_file.unlink(missing_ok=True)

def parse_zipcodes_file(content):
    """Parse the ZIP Codes by District XLS file."""
    temp_file = Path("temp_zipcodes.xls")
    temp_file.write_bytes(content)
    
    try:
        df = pd.read_excel(temp_file, engine='xlrd')
        print(f"  Loaded {len(df)} rows, columns: {list(df.columns)}")
        
        # Build mapping
        district_data = defaultdict(list)
        
        for _, row in df.iterrows():
            district = None
            zipcode = None
            
            for col in df.columns:
                col_lower = str(col).lower()
                if 'district' in col_lower and district is None:
                    district = str(row[col]).strip()
                elif 'zip' in col_lower:
                    zipcode = str(row[col]).strip()
            
            if district and zipcode and district != 'nan' and zipcode != 'nan':
                if zipcode not in district_data[district]:
                    district_data[district].append(zipcode)
        
        # Convert to regular dict and sort
        result = {}
        for district in sorted(district_data.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            result[district] = {
                'zipcodes': sorted(district_data[district]),
                'total_zipcodes': len(district_data[district])
            }
        
        return result
        
    finally:
        temp_file.unlink(missing_ok=True)

def main():
    """Download and parse all district reference files."""
    
    print("="*80)
    print("BUILDING DISTRICT REFERENCE DATA FROM TEXAS LEGISLATURE")
    print("="*80)
    print()
    
    output_dir = Path("WhoVoted/data/district_reference")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    all_data = {}
    
    # Process each file type
    for file_type, file_info in FILES.items():
        print(f"\n{file_info['description']} ({file_info['name']}):")
        print("-" * 60)
        
        content = download_file(file_info['name'])
        
        if not content:
            print(f"  ✗ Could not download {file_info['name']}")
            print(f"  Please manually download from: https://data.capitol.texas.gov/dataset/planc2333")
            continue
        
        # Parse based on file type
        if file_type == 'counties':
            data = parse_counties_file(content)
        elif file_type == 'precincts':
            data = parse_precincts_file(content)
        elif file_type == 'zipcodes':
            data = parse_zipcodes_file(content)
        else:
            continue
        
        # Save individual file
        output_file = output_dir / file_info['output']
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"  ✓ Saved to {output_file}")
        
        all_data[file_type] = data
    
    # Display summary for key districts
    print("\n" + "="*80)
    print("SUMMARY FOR KEY DISTRICTS")
    print("="*80)
    
    for district_num in ['15', '28', '34']:
        print(f"\n{'='*80}")
        print(f"TX-{district_num} CONGRESSIONAL DISTRICT")
        print(f"{'='*80}")
        
        if 'counties' in all_data and district_num in all_data['counties']:
            county_info = all_data['counties'][district_num]
            print(f"\nCounties: {county_info['total_counties']}")
            for county in county_info['counties']:
                split_marker = " (partial)" if county in county_info['split_counties'] else ""
                print(f"  - {county}{split_marker}")
        
        if 'precincts' in all_data and district_num in all_data['precincts']:
            precinct_info = all_data['precincts'][district_num]
            print(f"\nPrecincts: {precinct_info['total_precincts']} across {precinct_info['total_counties']} counties")
            for county, precincts in list(precinct_info['by_county'].items())[:5]:
                print(f"  {county}: {len(precincts)} precincts")
            if len(precinct_info['by_county']) > 5:
                print(f"  ... and {len(precinct_info['by_county']) - 5} more counties")
        
        if 'zipcodes' in all_data and district_num in all_data['zipcodes']:
            zip_info = all_data['zipcodes'][district_num]
            print(f"\nZIP Codes: {zip_info['total_zipcodes']}")
    
    print("\n" + "="*80)
    print("✓ DISTRICT REFERENCE DATA BUILD COMPLETE")
    print("="*80)
    print(f"\nFiles saved to: {output_dir}/")
    print("  - district_counties.json")
    print("  - district_precincts.json")
    print("  - district_zipcodes.json")

if __name__ == '__main__':
    main()
