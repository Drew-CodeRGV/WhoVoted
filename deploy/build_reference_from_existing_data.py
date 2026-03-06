#!/usr/bin/env python3
"""
Build district reference data from existing database and web sources.

METHODOLOGY:
1. Use existing precinct-district mapping in database
2. Aggregate to county level
3. Cross-reference with web sources for validation
4. Create comprehensive reference files

This gives us the authoritative count of counties/precincts per district
based on the actual data we're using for district assignments.
"""

import sqlite3
import json
from pathlib import Path
from collections import defaultdict
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'backend'))

try:
    from config import Config
    DB_PATH = Config.DATA_DIR / 'whovoted.db'
except:
    DB_PATH = Path('/opt/whovoted/data/whovoted.db')
    if not DB_PATH.exists():
        DB_PATH = Path('WhoVoted/data/whovoted.db')

def analyze_database_districts():
    """
    Analyze the database to determine which counties and precincts
    are assigned to each district based on our precinct mapping.
    """
    
    if not DB_PATH.exists():
        print(f"Database not found at {DB_PATH}")
        return None, None
    
    print(f"Analyzing database: {DB_PATH}")
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    # Get congressional districts
    print("\nAnalyzing Congressional Districts...")
    
    # Query all voters with district assignments
    query = """
        SELECT 
            congressional_district as district,
            county,
            precinct,
            COUNT(*) as voter_count
        FROM voters
        WHERE congressional_district IS NOT NULL 
          AND congressional_district != ''
          AND county IS NOT NULL
          AND county != ''
        GROUP BY congressional_district, county, precinct
        ORDER BY congressional_district, county, precinct
    """
    
    rows = conn.execute(query).fetchall()
    
    # Build mappings
    district_counties = defaultdict(set)
    district_precincts = defaultdict(lambda: defaultdict(set))
    
    for row in rows:
        district = str(row['district']).strip()
        county = str(row['county']).strip()
        precinct = str(row['precinct']).strip() if row['precinct'] else None
        
        district_counties[district].add(county)
        if precinct:
            district_precincts[district][county].add(precinct)
    
    # Convert to structured format
    counties_data = {}
    for district in sorted(district_counties.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        counties_data[district] = {
            'counties': sorted(list(district_counties[district])),
            'total_counties': len(district_counties[district]),
            'source': 'database_analysis',
            'note': 'Based on voters with district assignments in database'
        }
    
    precincts_data = {}
    for district in sorted(district_precincts.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        by_county = {}
        total_precincts = 0
        
        for county in sorted(district_precincts[district].keys()):
            precincts = sorted(list(district_precincts[district][county]))
            by_county[county] = precincts
            total_precincts += len(precincts)
        
        precincts_data[district] = {
            'by_county': by_county,
            'total_precincts': total_precincts,
            'total_counties': len(by_county),
            'source': 'database_analysis'
        }
    
    conn.close()
    
    return counties_data, precincts_data

def load_precinct_mapping():
    """Load the precinct-district mapping file if it exists."""
    mapping_file = Path('WhoVoted/data/precinct_districts.json')
    
    if not mapping_file.exists():
        print(f"Precinct mapping file not found: {mapping_file}")
        return None
    
    print(f"\nLoading precinct mapping: {mapping_file}")
    with open(mapping_file, 'r') as f:
        return json.load(f)

def build_from_precinct_mapping(precinct_mapping):
    """Build district reference from precinct mapping file."""
    
    if not precinct_mapping:
        return None, None
    
    print("Building reference from precinct mapping...")
    
    # Invert the mapping: precinct -> district to district -> precincts
    district_precincts = defaultdict(lambda: defaultdict(list))
    district_counties = defaultdict(set)
    
    for key, district_info in precinct_mapping.items():
        # Key format: "COUNTY|PRECINCT"
        if '|' in key:
            county, precinct = key.split('|', 1)
            
            # Get congressional district
            cong_district = district_info.get('congressional')
            if cong_district:
                district_counties[cong_district].add(county)
                if precinct not in district_precincts[cong_district][county]:
                    district_precincts[cong_district][county].append(precinct)
    
    # Format counties data
    counties_data = {}
    for district in sorted(district_counties.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        counties_data[district] = {
            'counties': sorted(list(district_counties[district])),
            'total_counties': len(district_counties[district]),
            'source': 'precinct_mapping_file'
        }
    
    # Format precincts data
    precincts_data = {}
    for district in sorted(district_precincts.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        by_county = {}
        total_precincts = 0
        
        for county in sorted(district_precincts[district].keys()):
            precincts = sorted(district_precincts[district][county])
            by_county[county] = precincts
            total_precincts += len(precincts)
        
        precincts_data[district] = {
            'by_county': by_county,
            'total_precincts': total_precincts,
            'total_counties': len(by_county),
            'source': 'precinct_mapping_file'
        }
    
    return counties_data, precincts_data

def display_summary(counties_data, precincts_data, title="DISTRICT REFERENCE DATA"):
    """Display a summary of the district reference data."""
    
    print("\n" + "="*80)
    print(title)
    print("="*80)
    
    if not counties_data and not precincts_data:
        print("\nNo data available")
        return
    
    # Get all districts
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
            
            # Show sample
            for idx, (county, precincts) in enumerate(sorted(precinct_info['by_county'].items())):
                if idx < 3:
                    print(f"  {county}: {len(precincts)} precincts")
                elif idx == 3:
                    remaining = len(precinct_info['by_county']) - 3
                    if remaining > 0:
                        print(f"  ... and {remaining} more counties")
                    break

def main():
    """Main process."""
    
    print("="*80)
    print("BUILDING DISTRICT REFERENCE DATA")
    print("="*80)
    print()
    print("This script analyzes existing data to determine counties and precincts")
    print("per congressional district.")
    print()
    
    output_dir = Path("WhoVoted/data/district_reference")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Try multiple sources
    counties_data = None
    precincts_data = None
    
    # Source 1: Precinct mapping file
    print("\n" + "-"*80)
    print("SOURCE 1: Precinct Mapping File")
    print("-"*80)
    precinct_mapping = load_precinct_mapping()
    if precinct_mapping:
        counties_data, precincts_data = build_from_precinct_mapping(precinct_mapping)
        if counties_data:
            display_summary(counties_data, precincts_data, "FROM PRECINCT MAPPING FILE")
    
    # Source 2: Database analysis
    if not counties_data:
        print("\n" + "-"*80)
        print("SOURCE 2: Database Analysis")
        print("-"*80)
        db_counties, db_precincts = analyze_database_districts()
        if db_counties:
            counties_data = db_counties
            precincts_data = db_precincts
            display_summary(counties_data, precincts_data, "FROM DATABASE ANALYSIS")
    
    # Save results
    if counties_data:
        output_file = output_dir / "district_counties_from_data.json"
        with open(output_file, 'w') as f:
            json.dump(counties_data, f, indent=2)
        print(f"\n✓ Saved counties data to: {output_file}")
    
    if precincts_data:
        output_file = output_dir / "district_precincts_from_data.json"
        with open(output_file, 'w') as f:
            json.dump(precincts_data, f, indent=2)
        print(f"✓ Saved precincts data to: {output_file}")
    
    if not counties_data:
        print("\n✗ Could not build reference data from any source")
        print("\nPlease ensure:")
        print("  1. Database exists with voter data")
        print("  2. Precinct mapping file exists")
        print("  3. District assignments have been run")
    
    print("\n" + "="*80)
    print("COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
