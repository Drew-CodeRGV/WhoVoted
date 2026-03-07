#!/usr/bin/env python3
"""
Build precinct_districts table from official district reference files
This provides precinct-level district assignments (the correct way)
"""
import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = Path('/opt/whovoted/data/district_reference')

# Official district reference files with VTD (precinct) data
FILES = {
    'congressional': DATA_DIR / 'PLANC2333_r110_VTD24G.xls',
    'state_senate': DATA_DIR / 'PLANS2168_r110_VTD24G.xls',
    'state_house': DATA_DIR / 'PLANH2316_r110_VTD24G.xls'
}

def log(msg):
    print(f"  {msg}")

def normalize_precinct(precinct_str):
    """Normalize precinct identifiers for matching"""
    if not precinct_str:
        return None
    # Remove leading zeros, dots, spaces
    precinct = str(precinct_str).strip().lstrip('0').replace('.', '').replace(' ', '')
    if not precinct:
        return '0'
    return precinct

def main():
    print("="*80)
    print("BUILDING PRECINCT-TO-DISTRICT MAPPING TABLE")
    print("="*80)
    
    conn = sqlite3.connect(DB_PATH, timeout=120.0)
    conn.execute('PRAGMA journal_mode=WAL')
    
    # Create table
    log("Creating precinct_districts table...")
    conn.execute("DROP TABLE IF EXISTS precinct_districts")
    conn.execute("""
        CREATE TABLE precinct_districts (
            county TEXT NOT NULL,
            precinct TEXT NOT NULL,
            congressional_district TEXT,
            state_senate_district TEXT,
            state_house_district TEXT,
            PRIMARY KEY (county, precinct)
        )
    """)
    
    total_mappings = 0
    
    for district_type, file_path in FILES.items():
        if not file_path.exists():
            log(f"⚠ {district_type} file not found: {file_path}")
            continue
        
        log(f"\nProcessing {district_type}: {file_path.name}")
        
        try:
            # Read Excel file
            df = pd.read_excel(file_path, sheet_name=0)
            
            # Find relevant columns
            # Typical columns: COUNTY, VTD (precinct), DISTRICT
            county_col = None
            precinct_col = None
            district_col = None
            
            for col in df.columns:
                col_upper = str(col).upper()
                if 'COUNTY' in col_upper:
                    county_col = col
                elif 'VTD' in col_upper or 'PRECINCT' in col_upper:
                    precinct_col = col
                elif 'DISTRICT' in col_upper or 'DIST' in col_upper:
                    district_col = col
            
            if not all([county_col, precinct_col, district_col]):
                log(f"  ✗ Could not find required columns")
                log(f"    Available columns: {list(df.columns)}")
                continue
            
            log(f"  Found columns: county={county_col}, precinct={precinct_col}, district={district_col}")
            
            # Process each row
            mappings = {}
            for _, row in df.iterrows():
                county = str(row[county_col]).strip()
                precinct = normalize_precinct(row[precinct_col])
                district = str(row[district_col]).strip()
                
                if not county or not precinct or not district:
                    continue
                
                key = (county, precinct)
                if key not in mappings:
                    mappings[key] = {}
                
                if district_type == 'congressional':
                    mappings[key]['congressional_district'] = district
                elif district_type == 'state_senate':
                    mappings[key]['state_senate_district'] = district
                elif district_type == 'state_house':
                    mappings[key]['state_house_district'] = district
            
            log(f"  Parsed {len(mappings):,} precinct mappings")
            
            # Insert into database
            for (county, precinct), districts in mappings.items():
                conn.execute("""
                    INSERT INTO precinct_districts (county, precinct, congressional_district, state_senate_district, state_house_district)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(county, precinct) DO UPDATE SET
                        congressional_district = COALESCE(excluded.congressional_district, precinct_districts.congressional_district),
                        state_senate_district = COALESCE(excluded.state_senate_district, precinct_districts.state_senate_district),
                        state_house_district = COALESCE(excluded.state_house_district, precinct_districts.state_house_district)
                """, (
                    county,
                    precinct,
                    districts.get('congressional_district'),
                    districts.get('state_senate_district'),
                    districts.get('state_house_district')
                ))
            
            total_mappings += len(mappings)
            conn.commit()
            log(f"  ✓ Inserted {len(mappings):,} mappings")
            
        except Exception as e:
            log(f"  ✗ Error processing {district_type}: {e}")
            continue
    
    # Create indexes
    log("\nCreating indexes...")
    conn.execute("CREATE INDEX idx_precinct_districts_county ON precinct_districts(county)")
    conn.execute("CREATE INDEX idx_precinct_districts_cong ON precinct_districts(congressional_district)")
    conn.commit()
    
    # Summary
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM precinct_districts")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT county) FROM precinct_districts")
    counties = cursor.fetchone()[0]
    
    print("\n" + "="*80)
    print("PRECINCT-TO-DISTRICT MAPPING COMPLETE")
    print("="*80)
    print(f"  Total mappings: {total:,}")
    print(f"  Counties covered: {counties}")
    print(f"  ✓ Ready for precinct-based district assignment")
    
    conn.close()

if __name__ == '__main__':
    main()
