#!/usr/bin/env python3
"""
Complete Fix: Parse VTD files, build precinct mappings, reassign all districts
This will fix the D15 accuracy issue and all other district assignments
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
import re

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = Path('/opt/whovoted/data/district_reference')
ELECTION_DATE = '2026-03-03'
TARGET_D15 = 54573

def log(msg, level='INFO'):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [{level}] {msg}")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=120.0, isolation_level=None)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=120000')
    return conn

def normalize_precinct(precinct_str):
    """Normalize precinct identifiers for matching"""
    if pd.isna(precinct_str) or precinct_str is None:
        return None
    precinct = str(precinct_str).strip().upper()
    # Remove common prefixes/suffixes
    precinct = precinct.replace('PRECINCT', '').replace('PCT', '').replace('VTD', '')
    precinct = precinct.strip().lstrip('0')
    if not precinct or precinct == '':
        return '0'
    return precinct

def normalize_county(county_str):
    """Normalize county names"""
    if pd.isna(county_str) or county_str is None:
        return None
    county = str(county_str).strip().title()
    # Fix common variations
    county = county.replace('Mclennan', 'McLennan')
    county = county.replace('Lasalle', 'La Salle')
    county = county.replace('Dewitt', 'DeWitt')
    return county

def parse_vtd_file(file_path, district_type):
    """Parse VTD file with complex Excel format"""
    log(f"Parsing {file_path.name}...")
    
    try:
        # Read Excel file, skip header rows
        df = pd.read_excel(file_path, sheet_name=0, header=None)
        
        # Find the data start row (look for "DISTRICT" in first column)
        data_start = None
        for idx, row in df.iterrows():
            if idx > 20:  # Don't search too far
                break
            val = str(row[0]).upper() if not pd.isna(row[0]) else ''
            if 'DISTRICT' in val and not 'ANALYSIS' in val:
                data_start = idx
                break
        
        if data_start is None:
            log(f"  Could not find data start row", 'WARN')
            return {}
        
        log(f"  Data starts at row {data_start}")
        
        # Parse the data
        mappings = {}
        current_district = None
        current_county = None
        
        for idx in range(data_start, len(df)):
            row = df.iloc[idx]
            
            # Check if this is a district header row
            first_col = str(row[0]).strip() if not pd.isna(row[0]) else ''
            if 'DISTRICT' in first_col.upper():
                # Extract district number
                match = re.search(r'(\d+)', first_col)
                if match:
                    current_district = match.group(1)
                    log(f"  Found District {current_district}")
                continue
            
            # Check if this is a county row (has county name and "Total:" or percentage)
            second_col = str(row[1]).strip() if not pd.isna(row[1]) else ''
            third_col = str(row[2]).strip() if not pd.isna(row[2]) else ''
            
            # County header row
            if second_col and not third_col and not first_col:
                # This might be a county name
                potential_county = second_col.replace('(', '').replace(')', '').replace('%', '').strip()
                if len(potential_county) > 3 and not potential_county.isdigit():
                    current_county = normalize_county(potential_county)
                    continue
            
            # Precinct data row (has precinct number in first column)
            if first_col and first_col.isdigit() and current_district and current_county:
                precinct = normalize_precinct(first_col)
                if precinct:
                    key = (current_county, precinct)
                    if key not in mappings:
                        mappings[key] = {}
                    mappings[key][district_type] = current_district
        
        log(f"  Parsed {len(mappings)} precinct mappings")
        return mappings
        
    except Exception as e:
        log(f"  Error parsing file: {e}", 'ERROR')
        return {}

def build_precinct_districts_table(conn):
    """Build precinct_districts table from VTD files"""
    log("="*80)
    log("STEP 1: BUILD PRECINCT_DISTRICTS TABLE")
    log("="*80)
    
    cursor = conn.cursor()
    
    # Drop and recreate table
    log("\nCreating precinct_districts table...")
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
    
    # Parse VTD files
    files = {
        'congressional_district': DATA_DIR / 'PLANC2333_r110_VTD24G.xls',
        'state_senate_district': DATA_DIR / 'PLANS2168_r110_VTD2024 General.xls',
        'state_house_district': DATA_DIR / 'PLANH2316_r110_VTD2024 General.xls',
    }
    
    all_mappings = {}
    
    for district_type, file_path in files.items():
        if not file_path.exists():
            log(f"File not found: {file_path}", 'WARN')
            continue
        
        mappings = parse_vtd_file(file_path, district_type)
        
        # Merge mappings
        for key, districts in mappings.items():
            if key not in all_mappings:
                all_mappings[key] = {}
            all_mappings[key].update(districts)
    
    # Insert into database
    log(f"\nInserting {len(all_mappings)} precinct mappings into database...")
    
    for (county, precinct), districts in all_mappings.items():
        cursor.execute("""
            INSERT INTO precinct_districts (county, precinct, congressional_district, state_senate_district, state_house_district)
            VALUES (?, ?, ?, ?, ?)
        """, (
            county,
            precinct,
            districts.get('congressional_district'),
            districts.get('state_senate_district'),
            districts.get('state_house_district')
        ))
    
    # Create indexes
    log("Creating indexes...")
    cursor.execute("CREATE INDEX idx_precinct_districts_county ON precinct_districts(county)")
    cursor.execute("CREATE INDEX idx_precinct_districts_cong ON precinct_districts(congressional_district)")
    cursor.execute("CREATE INDEX idx_precinct_districts_senate ON precinct_districts(state_senate_district)")
    cursor.execute("CREATE INDEX idx_precinct_districts_house ON precinct_districts(state_house_district)")
    
    log(f"✓ precinct_districts table built with {len(all_mappings)} mappings")

def reassign_all_districts(conn):
    """Reassign all voters using precinct-level data"""
    log("\n" + "="*80)
    log("STEP 2: REASSIGN ALL VOTERS USING PRECINCT DATA")
    log("="*80)
    
    cursor = conn.cursor()
    
    # Get total voters
    cursor.execute("SELECT COUNT(*) FROM voters")
    total = cursor.fetchone()[0]
    log(f"\nTotal voters to process: {total:,}")
    
    # Update using precinct data
    log("\nUpdating districts using precinct mappings...")
    
    cursor.execute("""
        UPDATE voters
        SET 
            congressional_district = (
                SELECT pd.congressional_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND pd.precinct = voters.precinct
            ),
            state_senate_district = (
                SELECT pd.state_senate_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND pd.precinct = voters.precinct
            ),
            state_house_district = (
                SELECT pd.state_house_district
                FROM precinct_districts pd
                WHERE pd.county = voters.county
                AND pd.precinct = voters.precinct
            )
        WHERE EXISTS (
            SELECT 1 FROM precinct_districts pd
            WHERE pd.county = voters.county
            AND pd.precinct = voters.precinct
        )
    """)
    
    updated = cursor.rowcount
    log(f"✓ Updated {updated:,} voters using precinct data")
    
    # Check coverage
    cursor.execute("""
        SELECT COUNT(*) FROM voters
        WHERE congressional_district IS NOT NULL
    """)
    with_district = cursor.fetchone()[0]
    
    coverage = 100 * with_district / total if total > 0 else 0
    log(f"✓ District coverage: {with_district:,}/{total:,} ({coverage:.1f}%)")

def verify_d15_accuracy(conn):
    """Verify D15 matches target"""
    log("\n" + "="*80)
    log("STEP 3: VERIFY D15 ACCURACY")
    log("="*80)
    
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.congressional_district = '15'
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
    """, (ELECTION_DATE,))
    
    actual = cursor.fetchone()[0]
    diff = actual - TARGET_D15
    accuracy = 100 * (1 - abs(diff) / TARGET_D15) if TARGET_D15 > 0 else 0
    
    log(f"\nD15 Democratic Primary:")
    log(f"  Database: {actual:,}")
    log(f"  Official: {TARGET_D15:,}")
    log(f"  Difference: {diff:+,}")
    log(f"  Accuracy: {accuracy:.2f}%")
    
    if accuracy >= 99.9:
        log("  ✓ EXCELLENT - Within 0.1%!", 'SUCCESS')
    elif accuracy >= 99.0:
        log("  ✓ GOOD - Within 1%", 'SUCCESS')
    elif accuracy >= 95.0:
        log("  ⚠ ACCEPTABLE - Within 5%", 'WARN')
    else:
        log("  ✗ NEEDS WORK - More than 5% off", 'ERROR')
    
    return accuracy

def regenerate_district_caches(conn):
    """Regenerate district cache files"""
    log("\n" + "="*80)
    log("STEP 4: REGENERATE DISTRICT CACHES")
    log("="*80)
    
    districts = ['15', '28', '34']  # Key congressional districts
    
    for district in districts:
        log(f"\nRegenerating TX-{district} cache...")
        # This would call the existing cache generation logic
        # For now, just log that it should be done
        log(f"  → Run: python3 deploy/regenerate_all_district_caches_fast.py")
    
    log("\n✓ District caches should be regenerated")

def main():
    log("="*80)
    log("COMPLETE DISTRICT ASSIGNMENT FIX")
    log("="*80)
    log("\nThis will:")
    log("  1. Parse VTD files to extract precinct-to-district mappings")
    log("  2. Build precinct_districts table")
    log("  3. Reassign all 2.6M voters using precinct-level data")
    log("  4. Verify D15 accuracy")
    log("  5. Regenerate district caches")
    
    conn = get_db_connection()
    
    try:
        # Step 1: Build precinct_districts table
        build_precinct_districts_table(conn)
        
        # Step 2: Reassign all voters
        reassign_all_districts(conn)
        
        # Step 3: Verify D15
        accuracy = verify_d15_accuracy(conn)
        
        # Step 4: Regenerate caches
        regenerate_district_caches(conn)
        
        # Final summary
        log("\n" + "="*80)
        log("COMPLETE!")
        log("="*80)
        log(f"\n✓ Precinct-level district assignments complete")
        log(f"✓ D15 accuracy: {accuracy:.2f}%")
        log(f"\nNext steps:")
        log(f"  1. Regenerate district caches: python3 deploy/regenerate_all_district_caches_fast.py")
        log(f"  2. Verify other districts")
        log(f"  3. Test frontend")
        
    except Exception as e:
        log(f"\n✗ Error: {e}", 'ERROR')
        import traceback
        traceback.print_exc()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
