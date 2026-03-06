#!/usr/bin/env python3
"""
Parse downloaded Texas Legislature district reference files.

INSTRUCTIONS FOR CONGRESSIONAL DISTRICTS:
1. Go to https://data.capitol.texas.gov/dataset/planc2333
2. Download these files to WhoVoted/data/district_reference/:
   - PLANC2333_r150.xls (Districts by County)
   - PLANC2333_r365_Prec24G.xls (Precincts in District by County)

INSTRUCTIONS FOR STATE SENATE DISTRICTS:
1. Go to https://data.capitol.texas.gov/dataset/plans2168
2. Download these files to WhoVoted/data/district_reference/:
   - PLANS2168_r150.xls (Districts by County)
   - PLANS2168_r365_Prec2024 General.xls (Precincts in District by County)

INSTRUCTIONS FOR STATE HOUSE DISTRICTS:
1. Go to https://data.capitol.texas.gov/dataset/planh2316
2. Download these files to WhoVoted/data/district_reference/:
   - PLANH2316_r150.xls (Districts by County)
   - PLANH2316_r365_Prec2024 General.xls (Precincts in District by County)

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
    print("PARSING TEXAS DISTRICT REFERENCE FILES")
    print("="*80)
    
    data_dir = Path("WhoVoted/data/district_reference")
    data_dir.mkdir(parents=True, exist_ok=True)
    
    # Track all parsed data
    all_counties_data = {}
    all_precincts_data = {}
    
    # ========== CONGRESSIONAL DISTRICTS (38 districts) ==========
    print("\n" + "="*80)
    print("CONGRESSIONAL DISTRICTS (PLANC2333)")
    print("="*80)
    
    # Parse Congressional counties file
    cong_counties_file = data_dir / "PLANC2333_r150.xls"
    if cong_counties_file.exists():
        counties_data = parse_counties_file(cong_counties_file)
        if counties_data:
            output_file = data_dir / "congressional_counties.json"
            with open(output_file, 'w') as f:
                json.dump(counties_data, f, indent=2)
            print(f"\n✓ Saved to {output_file}")
            all_counties_data['congressional'] = counties_data
    else:
        print(f"\n✗ File not found: {cong_counties_file}")
        print("  Please download PLANC2333_r150.xls from:")
        print("  https://data.capitol.texas.gov/dataset/planc2333")
        counties_data = None
    
    # Parse Congressional precincts file
    cong_precincts_file = data_dir / "PLANC2333_r365_Prec24G.xls"
    if cong_precincts_file.exists():
        precincts_data = parse_precincts_file(cong_precincts_file)
        if precincts_data:
            output_file = data_dir / "congressional_precincts.json"
            with open(output_file, 'w') as f:
                json.dump(precincts_data, f, indent=2)
            print(f"\n✓ Saved to {output_file}")
            all_precincts_data['congressional'] = precincts_data
    else:
        print(f"\n✗ File not found: {cong_precincts_file}")
        print("  Please download PLANC2333_r365_Prec24G.xls from:")
        print("  https://data.capitol.texas.gov/dataset/planc2333")
        precincts_data = None
    
    # ========== STATE SENATE DISTRICTS (31 districts) ==========
    print("\n" + "="*80)
    print("STATE SENATE DISTRICTS (PLANS2168)")
    print("="*80)
    
    # Parse State Senate counties file
    senate_counties_file = data_dir / "PLANS2168_r150.xls"
    if senate_counties_file.exists():
        senate_counties_data = parse_counties_file(senate_counties_file)
        if senate_counties_data:
            output_file = data_dir / "state_senate_counties.json"
            with open(output_file, 'w') as f:
                json.dump(senate_counties_data, f, indent=2)
            print(f"\n✓ Saved to {output_file}")
            all_counties_data['state_senate'] = senate_counties_data
    else:
        print(f"\n✗ File not found: {senate_counties_file}")
        print("  Please download PLANS2168_r150.xls from:")
        print("  https://data.capitol.texas.gov/dataset/plans2168")
        senate_counties_data = None
    
    # Parse State Senate precincts file (try multiple naming patterns)
    senate_precincts_patterns = [
        "PLANS2168_r365_Prec2024 General.xls",
        "PLANS2168_r365_Prec24G.xls",
        "PLANS2168_r365_VTD2024 General.xls"
    ]
    
    senate_precincts_data = None
    for pattern in senate_precincts_patterns:
        senate_precincts_file = data_dir / pattern
        if senate_precincts_file.exists():
            senate_precincts_data = parse_precincts_file(senate_precincts_file)
            if senate_precincts_data:
                output_file = data_dir / "state_senate_precincts.json"
                with open(output_file, 'w') as f:
                    json.dump(senate_precincts_data, f, indent=2)
                print(f"\n✓ Saved to {output_file}")
                all_precincts_data['state_senate'] = senate_precincts_data
            break
    
    if not senate_precincts_data:
        print(f"\n✗ File not found: PLANS2168_r365_Prec2024 General.xls")
        print("  Please download from:")
        print("  https://data.capitol.texas.gov/dataset/plans2168")
        print("  (Look for 'Precincts in District by County' XLS file)")
    
    # ========== STATE HOUSE DISTRICTS (150 districts) ==========
    print("\n" + "="*80)
    print("STATE HOUSE DISTRICTS (PLANH2316)")
    print("="*80)
    
    # Parse State House counties file
    house_counties_file = data_dir / "PLANH2316_r150.xls"
    if house_counties_file.exists():
        house_counties_data = parse_counties_file(house_counties_file)
        if house_counties_data:
            output_file = data_dir / "state_house_counties.json"
            with open(output_file, 'w') as f:
                json.dump(house_counties_data, f, indent=2)
            print(f"\n✓ Saved to {output_file}")
            all_counties_data['state_house'] = house_counties_data
    else:
        print(f"\n✗ File not found: {house_counties_file}")
        print("  Please download PLANH2316_r150.xls from:")
        print("  https://data.capitol.texas.gov/dataset/planh2316")
        house_counties_data = None
    
    # Parse State House precincts file (try multiple naming patterns)
    house_precincts_patterns = [
        "PLANH2316_r365_Prec2024 General.xls",
        "PLANH2316_r365_Prec24G.xls",
        "PLANH2316_r365_VTD2024 General.xls"
    ]
    
    house_precincts_data = None
    for pattern in house_precincts_patterns:
        house_precincts_file = data_dir / pattern
        if house_precincts_file.exists():
            house_precincts_data = parse_precincts_file(house_precincts_file)
            if house_precincts_data:
                output_file = data_dir / "state_house_precincts.json"
                with open(output_file, 'w') as f:
                    json.dump(house_precincts_data, f, indent=2)
                print(f"\n✓ Saved to {output_file}")
                all_precincts_data['state_house'] = house_precincts_data
            break
    
    if not house_precincts_data:
        print(f"\n✗ File not found: PLANH2316_r365_Prec2024 General.xls")
        print("  Please download from:")
        print("  https://data.capitol.texas.gov/dataset/planh2316")
        print("  (Look for 'Precincts in District by County' XLS file)")
    
    # Use the first parsed data for summary (backwards compatibility)
    counties_data = all_counties_data.get('congressional')
    precincts_data = all_precincts_data.get('congressional')
    
    # Display summary
    if all_counties_data or all_precincts_data:
        print("\n" + "="*80)
        print("SUMMARY - ALL DISTRICTS")
        print("="*80)
        
        # Display Congressional Districts
        if 'congressional' in all_counties_data or 'congressional' in all_precincts_data:
            print("\n" + "="*80)
            print("CONGRESSIONAL DISTRICTS (38 total)")
            print("="*80)
            
            cong_counties = all_counties_data.get('congressional', {})
            cong_precincts = all_precincts_data.get('congressional', {})
            
            all_cong_districts = set()
            all_cong_districts.update(cong_counties.keys())
            all_cong_districts.update(cong_precincts.keys())
            
            for district in sorted(all_cong_districts, key=lambda x: int(x) if x.isdigit() else 999):
                print(f"\n{'='*80}")
                print(f"TX-{district} CONGRESSIONAL DISTRICT")
                print(f"{'='*80}")
                
                if district in cong_counties:
                    county_info = cong_counties[district]
                    print(f"\nCOUNTIES: {county_info['total_counties']}")
                    for county in county_info['counties']:
                        print(f"  - {county}")
                
                if district in cong_precincts:
                    precinct_info = cong_precincts[district]
                    print(f"\nPRECINCTS: {precinct_info['total_precincts']} across {precinct_info['total_counties']} counties")
                    
                    # Show first 5 counties with precinct counts
                    for idx, (county, precincts) in enumerate(sorted(precinct_info['by_county'].items())):
                        if idx < 5:
                            print(f"  {county}: {len(precincts)} precincts")
                        else:
                            remaining = len(precinct_info['by_county']) - 5
                            print(f"  ... and {remaining} more counties")
                            break
        
        # Display State Senate Districts
        if 'state_senate' in all_counties_data or 'state_senate' in all_precincts_data:
            print("\n" + "="*80)
            print("STATE SENATE DISTRICTS (31 total)")
            print("="*80)
            
            senate_counties = all_counties_data.get('state_senate', {})
            senate_precincts = all_precincts_data.get('state_senate', {})
            
            all_senate_districts = set()
            all_senate_districts.update(senate_counties.keys())
            all_senate_districts.update(senate_precincts.keys())
            
            for district in sorted(all_senate_districts, key=lambda x: int(x) if x.isdigit() else 999):
                print(f"\n{'='*80}")
                print(f"SD-{district} STATE SENATE DISTRICT")
                print(f"{'='*80}")
                
                if district in senate_counties:
                    county_info = senate_counties[district]
                    print(f"\nCOUNTIES: {county_info['total_counties']}")
                    for county in county_info['counties']:
                        print(f"  - {county}")
                
                if district in senate_precincts:
                    precinct_info = senate_precincts[district]
                    print(f"\nPRECINCTS: {precinct_info['total_precincts']} across {precinct_info['total_counties']} counties")
                    
                    # Show first 5 counties with precinct counts
                    for idx, (county, precincts) in enumerate(sorted(precinct_info['by_county'].items())):
                        if idx < 5:
                            print(f"  {county}: {len(precincts)} precincts")
                        else:
                            remaining = len(precinct_info['by_county']) - 5
                            print(f"  ... and {remaining} more counties")
                            break
        
        # Display State House Districts
        if 'state_house' in all_counties_data or 'state_house' in all_precincts_data:
            print("\n" + "="*80)
            print("STATE HOUSE DISTRICTS (150 total)")
            print("="*80)
            
            house_counties = all_counties_data.get('state_house', {})
            house_precincts = all_precincts_data.get('state_house', {})
            
            all_house_districts = set()
            all_house_districts.update(house_counties.keys())
            all_house_districts.update(house_precincts.keys())
            
            # Show first 10 districts as sample
            sample_districts = sorted(all_house_districts, key=lambda x: int(x) if x.isdigit() else 999)[:10]
            
            for district in sample_districts:
                print(f"\n{'='*80}")
                print(f"HD-{district} STATE HOUSE DISTRICT")
                print(f"{'='*80}")
                
                if district in house_counties:
                    county_info = house_counties[district]
                    print(f"\nCOUNTIES: {county_info['total_counties']}")
                    for county in county_info['counties'][:5]:  # Show first 5
                        print(f"  - {county}")
                    if county_info['total_counties'] > 5:
                        print(f"  ... and {county_info['total_counties'] - 5} more")
                
                if district in house_precincts:
                    precinct_info = house_precincts[district]
                    print(f"\nPRECINCTS: {precinct_info['total_precincts']} across {precinct_info['total_counties']} counties")
            
            if len(all_house_districts) > 10:
                print(f"\n... and {len(all_house_districts) - 10} more House districts")
        
        print("\n" + "="*80)
        print("✓ PARSING COMPLETE")
        print("="*80)

if __name__ == '__main__':
    main()
