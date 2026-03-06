#!/usr/bin/env python3
"""
Parse downloaded Texas Legislature district reference files.

INSTRUCTIONS:
1. Go to https://data.capitol.texas.gov/dataset/planc2333
2. Download these files to WhoVoted/data/district_reference/:
   - PLANC2333_r150.xls (Districts by County)
   - PLANC2333_r365_Prec24G.xls (Precincts in District by County)
3. Run this script to parse them

This will create comprehensive JSON files showing counties and precincts per district.
"""

import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

def parse_counties_file(filepath):
    """Parse the Districts by County XLS file."""
    print(f"\nParsing {filepath.name}...")
    
    try:
        # Try different engines
        try:
            df = pd.read_excel(filepath, engine='xlrd')
        except:
            df = pd.read_excel(filepath, engine='openpyxl')
        
        print(f"  Loaded {len(df)} rows")
        print(f"  Columns: {list(df.columns)}")
        
        # Show first few rows to understand structure
        print("\n  First 10 rows:")
        print(df.head(10).to_string())
        
        # Build mapping - try to identify columns intelligently
        district_data = defaultdict(lambda: {'counties': [], 'split_counties': []})
        
        # Find district and county columns
        district_col = None
        county_col = None
        
        for col in df.columns:
            col_str = str(col).lower()
            if 'district' in col_str and district_col is None:
                district_col = col
            elif 'county' in col_str and 'split' not in col_str and county_col is None:
                county_col = col
        
        print(f"\n  Using columns: District='{district_col}', County='{county_col}'")
        
        if not district_col or not county_col:
            print("  ERROR: Could not identify district and county columns")
            return None
        
        # Parse data
        for idx, row in df.iterrows():
            try:
                district = str(row[district_col]).strip()
                county = str(row[county_col]).strip()
                
                # Skip header rows and invalid data
                if district in ['nan', 'District', ''] or county in ['nan', 'County', '']:
                    continue
                
                # Clean district number (remove "District " prefix if present)
                district = district.replace('District', '').replace('DISTRICT', '').strip()
                
                if county not in district_data[district]['counties']:
                    district_data[district]['counties'].append(county)
                    
            except Exception as e:
                print(f"  Warning: Skipping row {idx}: {e}")
                continue
        
        # Convert to regular dict and sort
        result = {}
        for district in sorted(district_data.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            result[district] = {
                'counties': sorted(district_data[district]['counties']),
                'total_counties': len(district_data[district]['counties'])
            }
        
        print(f"\n  ✓ Parsed {len(result)} districts")
        return result
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_precincts_file(filepath):
    """Parse the Precincts in District by County XLS file."""
    print(f"\nParsing {filepath.name}...")
    
    try:
        # Try different engines
        try:
            df = pd.read_excel(filepath, engine='xlrd')
        except:
            df = pd.read_excel(filepath, engine='openpyxl')
        
        print(f"  Loaded {len(df)} rows")
        print(f"  Columns: {list(df.columns)}")
        
        # Show first few rows
        print("\n  First 10 rows:")
        print(df.head(10).to_string())
        
        # Build mapping
        district_data = defaultdict(lambda: defaultdict(list))
        
        # Find columns
        district_col = None
        county_col = None
        precinct_col = None
        
        for col in df.columns:
            col_str = str(col).lower()
            if 'district' in col_str and district_col is None:
                district_col = col
            elif 'county' in col_str and county_col is None:
                county_col = col
            elif 'precinct' in col_str or 'pct' in col_str:
                precinct_col = col
        
        print(f"\n  Using columns: District='{district_col}', County='{county_col}', Precinct='{precinct_col}'")
        
        if not all([district_col, county_col, precinct_col]):
            print("  ERROR: Could not identify required columns")
            return None
        
        # Parse data
        for idx, row in df.iterrows():
            try:
                district = str(row[district_col]).strip()
                county = str(row[county_col]).strip()
                precinct = str(row[precinct_col]).strip()
                
                # Skip invalid data
                if any(x in ['nan', '', 'District', 'County', 'Precinct'] for x in [district, county, precinct]):
                    continue
                
                # Clean district number
                district = district.replace('District', '').replace('DISTRICT', '').strip()
                
                if precinct not in district_data[district][county]:
                    district_data[district][county].append(precinct)
                    
            except Exception as e:
                print(f"  Warning: Skipping row {idx}: {e}")
                continue
        
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
        
        print(f"\n  ✓ Parsed {len(result)} districts")
        return result
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    """Parse all available district reference files."""
    
    print("="*80)
    print("PARSING TEXAS CONGRESSIONAL DISTRICT REFERENCE FILES")
    print("="*80)
    
    data_dir = Path("WhoVoted/data/district_reference")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Parse counties file
    counties_file = data_dir / "PLANC2333_r150.xls"
    if counties_file.exists():
        counties_data = parse_counties_file(counties_file)
        if counties_data:
            output_file = data_dir / "district_counties.json"
            with open(output_file, 'w') as f:
                json.dump(counties_data, f, indent=2)
            print(f"\n✓ Saved to {output_file}")
    else:
        print(f"\n✗ File not found: {counties_file}")
        print("  Please download PLANC2333_r150.xls from:")
        print("  https://data.capitol.texas.gov/dataset/planc2333")
        counties_data = None
    
    # Parse precincts file
    precincts_file = data_dir / "PLANC2333_r365_Prec24G.xls"
    if precincts_file.exists():
        precincts_data = parse_precincts_file(precincts_file)
        if precincts_data:
            output_file = data_dir / "district_precincts.json"
            with open(output_file, 'w') as f:
                json.dump(precincts_data, f, indent=2)
            print(f"\n✓ Saved to {output_file}")
    else:
        print(f"\n✗ File not found: {precincts_file}")
        print("  Please download PLANC2333_r365_Prec24G.xls from:")
        print("  https://data.capitol.texas.gov/dataset/planc2333")
        precincts_data = None
    
    # Display summary
    if counties_data or precincts_data:
        print("\n" + "="*80)
        print("SUMMARY - ALL CONGRESSIONAL DISTRICTS")
        print("="*80)
        
        # Get all district numbers
        all_districts = set()
        if counties_data:
            all_districts.update(counties_data.keys())
        if precincts_data:
            all_districts.update(precincts_data.keys())
        
        for district in sorted(all_districts, key=lambda x: int(x) if x.isdigit() else 999):
            print(f"\n{'='*80}")
            print(f"TX-{district} CONGRESSIONAL DISTRICT")
            print(f"{'='*80}")
            
            if counties_data and district in counties_data:
                county_info = counties_data[district]
                print(f"\nCOUNTIES: {county_info['total_counties']}")
                for county in county_info['counties']:
                    print(f"  - {county}")
            
            if precincts_data and district in precincts_data:
                precinct_info = precincts_data[district]
                print(f"\nPRECINCTS: {precinct_info['total_precincts']} across {precinct_info['total_counties']} counties")
                
                # Show first 5 counties with precinct counts
                for idx, (county, precincts) in enumerate(sorted(precinct_info['by_county'].items())):
                    if idx < 5:
                        print(f"  {county}: {len(precincts)} precincts")
                    else:
                        remaining = len(precinct_info['by_county']) - 5
                        print(f"  ... and {remaining} more counties")
                        break
        
        print("\n" + "="*80)
        print("✓ PARSING COMPLETE")
        print("="*80)

if __name__ == '__main__':
    main()
