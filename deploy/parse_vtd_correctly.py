#!/usr/bin/env python3
"""
Correctly parse VTD files based on actual structure
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import re

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = Path('/opt/whovoted/data/district_reference')

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def normalize_precinct(precinct_str):
    """Normalize precinct for matching"""
    if pd.isna(precinct_str):
        return None
    p = str(precinct_str).strip().upper().replace(' ', '')
    # Keep leading zeros for now - we'll try multiple formats when matching
    return p if p else None

def normalize_county(county_str):
    """Normalize county name"""
    if pd.isna(county_str):
        return None
    # Remove percentage and parentheses
    county = re.sub(r'\s*\([^)]*\)', '', str(county_str))
    county = county.strip().title()
    # Fix common variations
    county = county.replace('Mclennan', 'McLennan')
    county = county.replace('Lasalle', 'La Salle')
    county = county.replace('Dewitt', 'DeWitt')
    return county

def parse_vtd_file(file_path):
    """Parse VTD file - returns dict of (county, precinct) -> district"""
    log(f"Parsing {file_path.name}...")
    
    df = pd.read_excel(file_path, sheet_name=0, header=None)
    
    mappings = {}
    current_district = None
    current_county = None
    
    for idx, row in df.iterrows():
        col2 = str(row[2]).strip() if pd.notna(row[2]) else ''
        
        # Check for district header (e.g., "DISTRICT 1")
        if 'DISTRICT' in col2.upper() and not 'ANALYSIS' in col2.upper():
            match = re.search(r'DISTRICT\s+(\d+)', col2, re.IGNORECASE)
            if match:
                current_district = match.group(1)
                log(f"  District {current_district}")
                continue
        
        # Check for county name (has parentheses with percentage)
        if '(' in col2 and '%' in col2 and current_district:
            current_county = normalize_county(col2)
            if current_county:
                log(f"    {current_county}")
            continue
        
        # Check for precinct (alphanumeric, not "Total:" or "VAP:")
        if col2 and col2 not in ['Total:', 'VAP:'] and current_district and current_county:
            # This might be a precinct
            precinct = normalize_precinct(col2)
            if precinct and not precinct.startswith('DISTRICT'):
                key = (current_county, precinct)
                mappings[key] = current_district
    
    log(f"  Parsed {len(mappings)} precinct mappings")
    return mappings

def build_precinct_table():
    """Build precinct_districts table"""
    log("="*80)
    log("BUILDING PRECINCT_DISTRICTS TABLE")
    log("="*80)
    
    conn = sqlite3.connect(DB_PATH, timeout=120.0)
    conn.execute('PRAGMA journal_mode=WAL')
    cursor = conn.cursor()
    
    # Create table
    log("\nCreating table...")
    cursor.execute("DROP TABLE IF EXISTS precinct_districts")
    cursor.execute("""
        CREATE TABLE precinct_districts (
            county TEXT NOT NULL,
            precinct TEXT NOT NULL,
            congressional_district TEXT,
            state_senate_district TEXT,
            state_house_district TEXT,
            PRIMARY KEY (county, precinct)
        )
    """)
    
    # Parse files
    files = {
        'congressional': DATA_DIR / 'PLANC2333_r110_VTD24G.xls',
        'senate': DATA_DIR / 'PLANS2168_r110_VTD2024 General.xls',
        'house': DATA_DIR / 'PLANH2316_r110_VTD2024 General.xls',
    }
    
    all_data = {}
    
    for district_type, file_path in files.items():
        if not file_path.exists():
            log(f"File not found: {file_path}")
            continue
        
        mappings = parse_vtd_file(file_path)
        
        for key, district in mappings.items():
            if key not in all_data:
                all_data[key] = {}
            all_data[key][district_type] = district
    
    # Insert
    log(f"\nInserting {len(all_data)} mappings...")
    for (county, precinct), districts in all_data.items():
        cursor.execute("""
            INSERT INTO precinct_districts (county, precinct, congressional_district, state_senate_district, state_house_district)
            VALUES (?, ?, ?, ?, ?)
        """, (
            county,
            precinct,
            districts.get('congressional'),
            districts.get('senate'),
            districts.get('house')
        ))
    
    conn.commit()
    
    # Create indexes
    log("Creating indexes...")
    cursor.execute("CREATE INDEX idx_pd_county ON precinct_districts(county)")
    cursor.execute("CREATE INDEX idx_pd_cong ON precinct_districts(congressional_district)")
    conn.commit()
    
    # Summary
    cursor.execute("SELECT COUNT(*) FROM precinct_districts")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT county) FROM precinct_districts")
    counties = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT congressional_district) FROM precinct_districts WHERE congressional_district IS NOT NULL")
    cong_districts = cursor.fetchone()[0]
    
    log(f"\n✓ Complete!")
    log(f"  Total mappings: {total:,}")
    log(f"  Counties: {counties}")
    log(f"  Congressional districts: {cong_districts}")
    
    conn.close()

if __name__ == '__main__':
    build_precinct_table()
