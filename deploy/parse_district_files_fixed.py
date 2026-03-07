#!/usr/bin/env python3
"""
Parse Texas Legislature district reference files with correct alternating row logic.
Creates comprehensive precinct-to-district mappings for all 219 districts.
"""

import pandas as pd
import json
from pathlib import Path
from collections import defaultdict

def parse_counties_file(filepath):
    """Parse Districts by County XLS - handles alternating row structure."""
    print(f"\nParsing {filepath.name}...")
    
    try:
        df = pd.read_excel(filepath, skiprows=6, engine='xlrd')
        print(f"  Loaded {len(df)} rows")
        
        # Parse alternating structure: County row, then District row(s)
        district_data = defaultdict(lambda: {'counties': [], 'split_counties': []})
        current_county = None
        
        for idx, row in df.iterrows():
            county = row.get('County')
            district = row.get('District')
            
            # Skip completely empty rows
            if pd.isna(county) and pd.isna(district):
                continue
            
            # County name row
            if pd.notna(county) and county not in ['County', '']:
                current_county = str(county).strip()
                # Check if this is a split county indicator
                if district == 'County Total':
                    # Next rows will have the districts this county is split into
                    continue
            
            # District number row
            elif pd.notna(district) and district != 'County Total':
                try:
                    district_num = str(int(float(district)))
                    if current_county and current_county not in district_data[district_num]['counties']:
                        district_data[district_num]['counties'].append(current_county)
                except (ValueError, TypeError):
                    continue
        
        # Convert to final format
        result = {}
        for district in sorted(district_data.keys(), key=lambda x: int(x) if x.isdigit() else 999):
            result[district] = {
                'counties': sorted(district_data[district]['counties']),
                'total_counties': len(district_data[district]['counties'])
            }
        
        print(f"  ✓ Parsed {len(result)} districts")
        return result
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_precincts_file(filepath):
    """Parse Precincts in District by County XLS."""
    print(f"\nParsing {filepath.name}...")
    
    try:
        df = pd.read_excel(filepath, skiprows=4, engine='xlrd')
        print(f"  Loaded {len(df)} rows")
        
        # Parse structure: County header, then precinct rows
        district_data = defaultdict(lambda: defaultdict(list))
        current_county = None
        
        for idx, row in df.iterrows():
            # Try to find county, precinct, district columns
            row_values = [str(v) for v in row.values if pd.notna(v)]
            
            # Skip empty rows
            if not row_values:
                continue
            
            # County header row (has county name but no precinct/district)
            if len(row_values) == 1:
                current_county = row_values[0].strip()
                continue
            
            # Precinct data row (has precinct and district)
            if len(row_values) >= 2 and current_county:
                try:
                    precinct = str(row_values[0]).strip()
                    district = str(int(float(row_values[1])))
                    
                    if precinct and district:
                        if precinct not in district_data[district][current_county]:
                            district_data[district][current_county].append(precinct)
                except (ValueError, TypeError, IndexError):
                    continue
        
        # Convert to final format
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
        
        print(f"  ✓ Parsed {len(result)} districts with {sum(r['total_precincts'] for r in result.values())} total precincts")
        return result
        
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return None

def main():
    print("="*80)
    print("PARSING TEXAS DISTRICT REFERENCE FILES")
    print("="*80)
    
    data_dir = Path("data/district_reference")
    
    # Parse all three district types
    all_data = {}
    
    # Congressional Districts
    print("\n" + "="*80)
    print("CONGRESSIONAL DISTRICTS (38 districts)")
    print("="*80)
    
    cong_counties = parse_counties_file(data_dir / "PLANC2333_r150.xls")
    if cong_counties:
        with open(data_dir / "congressional_counties.json", 'w') as f:
            json.dump(cong_counties, f, indent=2)
        all_data['congressional_counties'] = cong_counties
    
    cong_precincts = parse_precincts_file(data_dir / "PLANC2333_r365_Prec24G.xls")
    if cong_precincts:
        with open(data_dir / "congressional_precincts.json", 'w') as f:
            json.dump(cong_precincts, f, indent=2)
        all_data['congressional_precincts'] = cong_precincts
    
    # State Senate Districts
    print("\n" + "="*80)
    print("STATE SENATE DISTRICTS (31 districts)")
    print("="*80)
    
    senate_counties = parse_counties_file(data_dir / "PLANS2168_r150.xls")
    if senate_counties:
        with open(data_dir / "state_senate_counties.json", 'w') as f:
            json.dump(senate_counties, f, indent=2)
        all_data['senate_counties'] = senate_counties
    
    # Try multiple precinct file patterns
    senate_precinct_files = [
        "PLANS2168_r365_Prec24G.xls",
        "PLANS2168_r365_Prec2024 General.xls",
        "PLANS2168_r365_VTD24G.xls"
    ]
    for filename in senate_precinct_files:
        filepath = data_dir / filename
        if filepath.exists():
            senate_precincts = parse_precincts_file(filepath)
            if senate_precincts:
                with open(data_dir / "state_senate_precincts.json", 'w') as f:
                    json.dump(senate_precincts, f, indent=2)
                all_data['senate_precincts'] = senate_precincts
            break
    
    # State House Districts
    print("\n" + "="*80)
    print("STATE HOUSE DISTRICTS (150 districts)")
    print("="*80)
    
    house_counties = parse_counties_file(data_dir / "PLANH2316_r150.xls")
    if house_counties:
        with open(data_dir / "state_house_counties.json", 'w') as f:
            json.dump(house_counties, f, indent=2)
        all_data['house_counties'] = house_counties
    
    # Try multiple precinct file patterns
    house_precinct_files = [
        "PLANH2316_r365_Prec24G.xls",
        "PLANH2316_r365_Prec2024 General.xls",
        "PLANH2316_r365_VTD24G.xls"
    ]
    for filename in house_precinct_files:
        filepath = data_dir / filename
        if filepath.exists():
            house_precincts = parse_precincts_file(filepath)
            if house_precincts:
                with open(data_dir / "state_house_precincts.json", 'w') as f:
                    json.dump(house_precincts, f, indent=2)
                all_data['house_precincts'] = house_precincts
            break
    
    # Summary
    print("\n" + "="*80)
    print("PARSING COMPLETE")
    print("="*80)
    print(f"\nCongressional: {len(all_data.get('congressional_counties', {}))} districts")
    print(f"State Senate: {len(all_data.get('senate_counties', {}))} districts")
    print(f"State House: {len(all_data.get('house_counties', {}))} districts")
    print(f"\nTotal: {len(all_data.get('congressional_counties', {})) + len(all_data.get('senate_counties', {})) + len(all_data.get('house_counties', {}))} districts")
    
    if 'congressional_precincts' in all_data:
        total_precincts = sum(d['total_precincts'] for d in all_data['congressional_precincts'].values())
        print(f"\nCongressional precincts mapped: {total_precincts}")
    
    if 'senate_precincts' in all_data:
        total_precincts = sum(d['total_precincts'] for d in all_data['senate_precincts'].values())
        print(f"State Senate precincts mapped: {total_precincts}")
    
    if 'house_precincts' in all_data:
        total_precincts = sum(d['total_precincts'] for d in all_data['house_precincts'].values())
        print(f"State House precincts mapped: {total_precincts}")

if __name__ == '__main__':
    main()
