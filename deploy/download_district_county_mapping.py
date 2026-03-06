#!/usr/bin/env python3
"""
Download and parse the official Texas Legislature district-county mapping.
This creates a reference file showing which counties are in each congressional district.
"""

import requests
import pandas as pd
import json
from pathlib import Path

# URL for the Districts by County report
URL = "https://data.capitol.texas.gov/dataset/b0e4ac3f-f911-4f0e-9e1a-e8c5e0b0e0e0/resource/8e5c5e5e-5e5e-5e5e-5e5e-5e5e5e5e5e5e/download/planc2333_r150.xls"

# Alternative direct URL pattern from Texas Legislature
DIRECT_URL = "https://redistricting.capitol.texas.gov/docs/plans/congress/PLANC2333/reports/PLANC2333_r150.xls"

def download_and_parse():
    """Download the Districts by County XLS file and parse it."""
    
    print("Downloading PLANC2333_r150.xls (Districts by County)...")
    
    # Try the direct URL first
    try:
        response = requests.get(DIRECT_URL, timeout=30)
        response.raise_for_status()
        
        # Save to temp file
        temp_file = Path("temp_r150.xls")
        with open(temp_file, 'wb') as f:
            f.write(response.content)
        
        print(f"Downloaded {len(response.content)} bytes")
        
        # Parse the XLS file
        print("Parsing XLS file...")
        df = pd.read_excel(temp_file)
        
        print(f"Loaded {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        print("\nFirst few rows:")
        print(df.head(10))
        
        # Build district-county mapping
        district_counties = {}
        
        for _, row in df.iterrows():
            # The format should have District and County columns
            # Adjust column names based on actual file structure
            district = str(row.get('District', row.get('DISTRICT', ''))).strip()
            county = str(row.get('County', row.get('COUNTY', ''))).strip()
            
            if district and county and district != 'nan' and county != 'nan':
                if district not in district_counties:
                    district_counties[district] = []
                if county not in district_counties[district]:
                    district_counties[district].append(county)
        
        # Sort and display results
        print("\n" + "="*80)
        print("CONGRESSIONAL DISTRICTS BY COUNTY")
        print("="*80)
        
        for district in sorted(district_counties.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            counties = sorted(district_counties[district])
            print(f"\nDistrict {district}: {len(counties)} counties")
            for county in counties:
                print(f"  - {county}")
        
        # Save to JSON
        output_file = Path("WhoVoted/data/district_county_mapping.json")
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(district_counties, f, indent=2)
        
        print(f"\n✓ Saved mapping to {output_file}")
        
        # Clean up temp file
        temp_file.unlink()
        
        return district_counties
        
    except Exception as e:
        print(f"Error: {e}")
        print("\nPlease manually download the file from:")
        print("https://data.capitol.texas.gov/dataset/planc2333")
        print("Look for: PLANC2333_r150.xls (Districts by County)")
        return None

if __name__ == '__main__':
    download_and_parse()
