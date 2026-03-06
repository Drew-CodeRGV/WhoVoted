#!/usr/bin/env python3
"""
Build district reference data using Census TIGER/Line relationship files.

The Census Bureau provides relationship files that map geographic entities:
- Block to Congressional District
- Block to County
- Block to VTD (Voting Tabulation District / Precinct)

By processing these relationships, we can determine which counties and
precincts are in each congressional district WITHOUT needing shapefiles.

Data Source: Census Bureau TIGER/Line 2020
"""

import requests
import pandas as pd
import json
from pathlib import Path
from collections import defaultdict
import io

# Census TIGER/Line relationship files for Texas (FIPS 48)
# These are TAB-delimited text files, not shapefiles
BLOCK_TO_CD_URL = "https://www2.census.gov/geo/tiger/TIGER2020/TABBLOCK20/tl_2020_48_tabblock20.zip"
BLOCK_ASSIGNMENT_URL = "https://www2.census.gov/geo/docs/maps-data/data/baf2020/BlockAssign_ST48_TX.txt"

# Alternative: Use the 2020 Census Block Assignment Files
# These directly map blocks to districts
BAF_URL_TEMPLATE = "https://www2.census.gov/geo/docs/maps-data/data/baf2020/BlockAssign_ST48_TX.txt"

def download_block_assignment_file():
    """
    Download the Census Block Assignment File for Texas.
    This file maps every census block to its districts.
    """
    print("Downloading Census Block Assignment File for Texas...")
    print(f"URL: {BAF_URL_TEMPLATE}")
    
    try:
        response = requests.get(BAF_URL_TEMPLATE, timeout=120)
        response.raise_for_status()
        
        print(f"  Downloaded {len(response.content):,} bytes")
        
        # Parse the tab-delimited file
        df = pd.read_csv(io.StringIO(response.text), sep='|', dtype=str)
        
        print(f"  Loaded {len(df):,} census blocks")
        print(f"  Columns: {list(df.columns)}")
        
        return df
        
    except Exception as e:
        print(f"  Error: {e}")
        return None

def extract_districts_from_baf(df):
    """
    Extract district-county-precinct relationships from Block Assignment File.
    
    BAF columns include:
    - COUNTYFP: County FIPS code
    - CD118: Congressional District (118th Congress)
    - VTDST: Voting Tabulation District (Precinct)
    """
    
    if df is None:
        return None, None
    
    print("\nProcessing Block Assignment File...")
    
    # Texas county FIPS to name mapping
    texas_counties = get_texas_county_names()
    
    # Build district mappings
    district_counties = defaultdict(set)
    district_precincts = defaultdict(lambda: defaultdict(set))
    
    # Group by congressional district
    for _, row in df.iterrows():
        cd = str(row.get('CD118', '')).strip()
        county_fips = str(row.get('COUNTYFP', '')).strip()
        vtd = str(row.get('VTDST', '')).strip()
        
        if not cd or cd == 'ZZ':  # ZZ means not in a district
            continue
        
        # Convert county FIPS to name
        county_name = texas_counties.get(county_fips, f"County_{county_fips}")
        
        district_counties[cd].add(county_name)
        
        if vtd:
            district_precincts[cd][county_name].add(vtd)
    
    # Format counties data
    counties_data = {}
    for district in sorted(district_counties.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        counties_data[district] = {
            'counties': sorted(list(district_counties[district])),
            'total_counties': len(district_counties[district]),
            'source': 'census_baf_2020',
            'source_url': BAF_URL_TEMPLATE
        }
    
    # Format precincts data
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
            'source': 'census_baf_2020'
        }
    
    return counties_data, precincts_data

def get_texas_county_names():
    """
    Return mapping of Texas county FIPS codes to names.
    Texas is state FIPS 48.
    """
    return {
        '001': 'Anderson', '003': 'Andrews', '005': 'Angelina', '007': 'Aransas',
        '009': 'Archer', '011': 'Armstrong', '013': 'Atascosa', '015': 'Austin',
        '017': 'Bailey', '019': 'Bandera', '021': 'Bastrop', '023': 'Baylor',
        '025': 'Bee', '027': 'Bell', '029': 'Bexar', '031': 'Blanco',
        '033': 'Borden', '035': 'Bosque', '037': 'Bowie', '039': 'Brazoria',
        '041': 'Brazos', '043': 'Brewster', '045': 'Briscoe', '047': 'Brooks',
        '049': 'Brown', '051': 'Burleson', '053': 'Burnet', '055': 'Caldwell',
        '057': 'Calhoun', '059': 'Callahan', '061': 'Cameron', '063': 'Camp',
        '065': 'Carson', '067': 'Cass', '069': 'Castro', '071': 'Chambers',
        '073': 'Cherokee', '075': 'Childress', '077': 'Clay', '079': 'Cochran',
        '081': 'Coke', '083': 'Coleman', '085': 'Collin', '087': 'Collingsworth',
        '089': 'Colorado', '091': 'Comal', '093': 'Comanche', '095': 'Concho',
        '097': 'Cooke', '099': 'Coryell', '101': 'Cottle', '103': 'Crane',
        '105': 'Crockett', '107': 'Crosby', '109': 'Culberson', '111': 'Dallam',
        '113': 'Dallas', '115': 'Dawson', '117': 'Deaf Smith', '119': 'Delta',
        '121': 'Denton', '123': 'DeWitt', '125': 'Dickens', '127': 'Dimmit',
        '129': 'Donley', '131': 'Duval', '133': 'Eastland', '135': 'Ector',
        '137': 'Edwards', '139': 'Ellis', '141': 'El Paso', '143': 'Erath',
        '145': 'Falls', '147': 'Fannin', '149': 'Fayette', '151': 'Fisher',
        '153': 'Floyd', '155': 'Foard', '157': 'Fort Bend', '159': 'Franklin',
        '161': 'Freestone', '163': 'Frio', '165': 'Gaines', '167': 'Galveston',
        '169': 'Garza', '171': 'Gillespie', '173': 'Glasscock', '175': 'Goliad',
        '177': 'Gonzales', '179': 'Gray', '181': 'Grayson', '183': 'Gregg',
        '185': 'Grimes', '187': 'Guadalupe', '189': 'Hale', '191': 'Hall',
        '193': 'Hamilton', '195': 'Hansford', '197': 'Hardeman', '199': 'Hardin',
        '201': 'Harris', '203': 'Harrison', '205': 'Hartley', '207': 'Haskell',
        '209': 'Hays', '211': 'Hemphill', '213': 'Henderson', '215': 'Hidalgo',
        '217': 'Hill', '219': 'Hockley', '221': 'Hood', '223': 'Hopkins',
        '225': 'Houston', '227': 'Howard', '229': 'Hudspeth', '231': 'Hunt',
        '233': 'Hutchinson', '235': 'Irion', '237': 'Jack', '239': 'Jackson',
        '241': 'Jasper', '243': 'Jeff Davis', '245': 'Jefferson', '247': 'Jim Hogg',
        '249': 'Jim Wells', '251': 'Johnson', '253': 'Jones', '255': 'Karnes',
        '257': 'Kaufman', '259': 'Kendall', '261': 'Kenedy', '263': 'Kent',
        '265': 'Kerr', '267': 'Kimble', '269': 'King', '271': 'Kinney',
        '273': 'Kleberg', '275': 'Knox', '277': 'Lamar', '279': 'Lamb',
        '281': 'Lampasas', '283': 'La Salle', '285': 'Lavaca', '287': 'Lee',
        '289': 'Leon', '291': 'Liberty', '293': 'Limestone', '295': 'Lipscomb',
        '297': 'Live Oak', '299': 'Llano', '301': 'Loving', '303': 'Lubbock',
        '305': 'Lynn', '307': 'McCulloch', '309': 'McLennan', '311': 'McMullen',
        '313': 'Madison', '315': 'Marion', '317': 'Martin', '319': 'Mason',
        '321': 'Matagorda', '323': 'Maverick', '325': 'Medina', '327': 'Menard',
        '329': 'Midland', '331': 'Milam', '333': 'Mills', '335': 'Mitchell',
        '337': 'Montague', '339': 'Montgomery', '341': 'Moore', '343': 'Morris',
        '345': 'Motley', '347': 'Nacogdoches', '349': 'Navarro', '351': 'Newton',
        '353': 'Nolan', '355': 'Nueces', '357': 'Ochiltree', '359': 'Oldham',
        '361': 'Orange', '363': 'Palo Pinto', '365': 'Panola', '367': 'Parker',
        '369': 'Parmer', '371': 'Pecos', '373': 'Polk', '375': 'Potter',
        '377': 'Presidio', '379': 'Rains', '381': 'Randall', '383': 'Reagan',
        '385': 'Real', '387': 'Red River', '389': 'Reeves', '391': 'Refugio',
        '393': 'Roberts', '395': 'Robertson', '397': 'Rockwall', '399': 'Runnels',
        '401': 'Rusk', '403': 'Sabine', '405': 'San Augustine', '407': 'San Jacinto',
        '409': 'San Patricio', '411': 'San Saba', '413': 'Schleicher', '415': 'Scurry',
        '417': 'Shackelford', '419': 'Shelby', '421': 'Sherman', '423': 'Smith',
        '425': 'Somervell', '427': 'Starr', '429': 'Stephens', '431': 'Sterling',
        '433': 'Stonewall', '435': 'Sutton', '437': 'Swisher', '439': 'Tarrant',
        '441': 'Taylor', '443': 'Terrell', '445': 'Terry', '447': 'Throckmorton',
        '449': 'Titus', '451': 'Tom Green', '453': 'Travis', '455': 'Trinity',
        '457': 'Tyler', '459': 'Upshur', '461': 'Upton', '463': 'Uvalde',
        '465': 'Val Verde', '467': 'Van Zandt', '469': 'Victoria', '471': 'Walker',
        '473': 'Waller', '475': 'Ward', '477': 'Washington', '479': 'Webb',
        '481': 'Wharton', '483': 'Wheeler', '485': 'Wichita', '487': 'Wilbarger',
        '489': 'Willacy', '491': 'Williamson', '493': 'Wilson', '495': 'Winkler',
        '497': 'Wise', '499': 'Wood', '501': 'Yoakum', '503': 'Young',
        '505': 'Zapata', '507': 'Zavala'
    }

def main():
    """Main process."""
    
    print("="*80)
    print("BUILDING DISTRICT REFERENCE FROM CENSUS DATA")
    print("="*80)
    print()
    print("Using Census Bureau Block Assignment Files to determine")
    print("which counties and precincts are in each congressional district.")
    print()
    
    # Download and process
    df = download_block_assignment_file()
    
    if df is None:
        print("\n✗ Failed to download Census data")
        print("\nAlternative: The file can be manually downloaded from:")
        print(BAF_URL_TEMPLATE)
        return
    
    counties_data, precincts_data = extract_districts_from_baf(df)
    
    if not counties_data:
        print("\n✗ Failed to extract district data")
        return
    
    # Save results
    output_dir = Path("WhoVoted/data/district_reference")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    counties_file = output_dir / "congressional_counties.json"
    with open(counties_file, 'w') as f:
        json.dump(counties_data, f, indent=2)
    print(f"\n✓ Saved counties data: {counties_file}")
    
    precincts_file = output_dir / "congressional_precincts.json"
    with open(precincts_file, 'w') as f:
        json.dump(precincts_data, f, indent=2)
    print(f"✓ Saved precincts data: {precincts_file}")
    
    # Display summary
    print("\n" + "="*80)
    print("SUMMARY - ALL 38 CONGRESSIONAL DISTRICTS")
    print("="*80)
    
    for district in sorted(counties_data.keys(), key=lambda x: int(x) if x.isdigit() else 999):
        county_info = counties_data[district]
        precinct_info = precincts_data.get(district, {})
        
        print(f"\nTX-{district}: {county_info['total_counties']} counties, {precinct_info.get('total_precincts', 0)} precincts")
    
    print("\n" + "="*80)
    print("✓ COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
