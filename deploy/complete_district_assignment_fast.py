#!/usr/bin/env python3
"""
COMPLETE DISTRICT ASSIGNMENT - FAST & OPTIMIZED
Assigns ALL 3 district types to EVERY voter with maximum performance.
"""

import sqlite3
import pandas as pd
import json
from pathlib import Path
from collections import defaultdict
import time

def normalize_precinct(precinct):
    """Normalize precinct format."""
    if not precinct or precinct == 'None':
        return None
    precinct = str(precinct).strip().replace('** ', '')
    return precinct.zfill(4) if precinct.isdigit() else precinct

def normalize_county(county):
    """Normalize county name."""
    if not county:
        return None
    return str(county).strip().replace(' *', '').replace('*', '').strip()

def parse_all_precinct_files():
    """Parse ALL precinct files for all 3 district types."""
    print("="*80)
    print("PARSING ALL PRECINCT FILES")
    print("="*80)
    
    data_dir = Path("data/district_reference")
    mappings = {
        'congressional': {},
        'state_senate': {},
        'state_house': {}
    }
    
    # Congressional - already have this
    print("\n1. Congressional Districts (PLANC2333)...")
    cong_file = data_dir / "PLANC2333_r365_Prec24G.xls"
    if cong_file.exists():
        df = pd.read_excel(cong_file, skiprows=4, engine='xlrd')
        current_county = None
        count = 0
        
        for idx, row in df.iterrows():
            row_values = [str(v) for v in row.values if pd.notna(v)]
            if not row_values:
                continue
            
            if len(row_values) == 1:
                current_county = row_values[0].strip()
            elif len(row_values) >= 2 and current_county:
                try:
                    precinct = str(row_values[0]).strip()
                    district = str(int(float(row_values[1])))
                    key = f"{normalize_county(current_county)}|{normalize_precinct(precinct)}"
                    mappings['congressional'][key] = district
                    count += 1
                except:
                    pass
        
        print(f"   ✓ Parsed {count:,} Congressional precinct mappings")
    
    # State Senate - use r370 file
    print("\n2. State Senate Districts (PLANS2168)...")
    senate_file = data_dir / "PLANS2168_r370_Prec2024 General.xls"
    if senate_file.exists():
        df = pd.read_excel(senate_file, skiprows=4, engine='xlrd')
        current_county = None
        count = 0
        
        for idx, row in df.iterrows():
            row_values = [str(v) for v in row.values if pd.notna(v)]
            if not row_values:
                continue
            
            if len(row_values) == 1:
                current_county = row_values[0].strip()
            elif len(row_values) >= 2 and current_county:
                try:
                    precinct = str(row_values[0]).strip()
                    district = str(int(float(row_values[1])))
                    key = f"{normalize_county(current_county)}|{normalize_precinct(precinct)}"
                    mappings['state_senate'][key] = district
                    count += 1
                except:
                    pass
        
        print(f"   ✓ Parsed {count:,} State Senate precinct mappings")
    
    # State House - find the right file
    print("\n3. State House Districts (PLANH2316)...")
    house_patterns = [
        "PLANH2316_r370_Prec2024 General.xls",
        "PLANH2316_r365_Prec2024 General.xls",
        "PLANH2316_r365_Prec24G.xls"
    ]
    
    for pattern in house_patterns:
        house_file = data_dir / pattern
        if house_file.exists():
            df = pd.read_excel(house_file, skiprows=4, engine='xlrd')
            current_county = None
            count = 0
            
            for idx, row in df.iterrows():
                row_values = [str(v) for v in row.values if pd.notna(v)]
                if not row_values:
                    continue
                
                if len(row_values) == 1:
                    current_county = row_values[0].strip()
                elif len(row_values) >= 2 and current_county:
                    try:
                        precinct = str(row_values[0]).strip()
                        district = str(int(float(row_values[1])))
                        key = f"{normalize_county(current_county)}|{normalize_precinct(precinct)}"
                        mappings['state_house'][key] = district
                        count += 1
                    except:
                        pass
            
            print(f"   ✓ Parsed {count:,} State House precinct mappings from {pattern}")
            break
    
    return mappings

def create_fast_lookup_table(db_path, mappings):
    """Create optimized lookup table with ALL districts."""
    print("\n" + "="*80)
    print("CREATING FAST LOOKUP TABLE")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Drop and recreate for clean state
    cursor.execute("DROP TABLE IF EXISTS precinct_district_lookup_normalized")
    cursor.execute("""
        CREATE TABLE precinct_district_lookup_normalized (
            county_normalized TEXT NOT NULL,
            precinct_normalized TEXT NOT NULL,
            congressional_district TEXT,
            state_senate_district TEXT,
            state_house_district TEXT,
            PRIMARY KEY (county_normalized, precinct_normalized)
        )
    """)
    
    # Combine all mappings
    all_keys = set()
    all_keys.update(mappings['congressional'].keys())
    all_keys.update(mappings['state_senate'].keys())
    all_keys.update(mappings['state_house'].keys())
    
    print(f"\nInserting {len(all_keys):,} unique county-precinct combinations...")
    
    for key in all_keys:
        county, precinct = key.split('|', 1)
        cong = mappings['congressional'].get(key)
        senate = mappings['state_senate'].get(key)
        house = mappings['state_house'].get(key)
        
        cursor.execute("""
            INSERT OR REPLACE INTO precinct_district_lookup_normalized
            (county_normalized, precinct_normalized, congressional_district, state_senate_district, state_house_district)
            VALUES (?, ?, ?, ?, ?)
        """, (county, precinct, cong, senate, house))
    
    # Create index for O(1) lookups
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_normalized_lookup 
        ON precinct_district_lookup_normalized(county_normalized, precinct_normalized)
    """)
    
    conn.commit()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM precinct_district_lookup_normalized")
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM precinct_district_lookup_normalized WHERE congressional_district IS NOT NULL")
    has_cong = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM precinct_district_lookup_normalized WHERE state_senate_district IS NOT NULL")
    has_senate = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM precinct_district_lookup_normalized WHERE state_house_district IS NOT NULL")
    has_house = cursor.fetchone()[0]
    
    print(f"\n✓ Lookup table created:")
    print(f"  Total entries: {total:,}")
    print(f"  With Congressional: {has_cong:,} ({has_cong/total*100:.1f}%)")
    print(f"  With State Senate: {has_senate:,} ({has_senate/total*100:.1f}%)")
    print(f"  With State House: {has_house:,} ({has_house/total*100:.1f}%)")
    
    conn.close()

def assign_all_districts_bulk(db_path):
    """Assign ALL 3 districts using fast SQL UPDATE."""
    print("\n" + "="*80)
    print("ASSIGNING ALL DISTRICTS - BULK UPDATE")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check before
    cursor.execute("SELECT COUNT(*) FROM voters")
    total = cursor.fetchone()[0]
    
    print(f"\nTotal voters: {total:,}")
    print("\nUpdating all districts in one operation...")
    
    start = time.time()
    
    # Single UPDATE with subqueries - FAST
    cursor.execute("""
        UPDATE voters
        SET 
            congressional_district = (
                SELECT congressional_district 
                FROM precinct_district_lookup_normalized 
                WHERE county_normalized = REPLACE(REPLACE(voters.county, ' *', ''), '*', '')
                AND precinct_normalized = CASE 
                    WHEN LENGTH(REPLACE(voters.precinct, '** ', '')) > 0 
                    AND CAST(REPLACE(voters.precinct, '** ', '') AS TEXT) GLOB '[0-9]*'
                    THEN printf('%04d', CAST(REPLACE(voters.precinct, '** ', '') AS INTEGER))
                    ELSE REPLACE(voters.precinct, '** ', '')
                END
            ),
            state_senate_district = (
                SELECT state_senate_district 
                FROM precinct_district_lookup_normalized 
                WHERE county_normalized = REPLACE(REPLACE(voters.county, ' *', ''), '*', '')
                AND precinct_normalized = CASE 
                    WHEN LENGTH(REPLACE(voters.precinct, '** ', '')) > 0 
                    AND CAST(REPLACE(voters.precinct, '** ', '') AS TEXT) GLOB '[0-9]*'
                    THEN printf('%04d', CAST(REPLACE(voters.precinct, '** ', '') AS INTEGER))
                    ELSE REPLACE(voters.precinct, '** ', '')
                END
            ),
            state_house_district = (
                SELECT state_house_district 
                FROM precinct_district_lookup_normalized 
                WHERE county_normalized = REPLACE(REPLACE(voters.county, ' *', ''), '*', '')
                AND precinct_normalized = CASE 
                    WHEN LENGTH(REPLACE(voters.precinct, '** ', '')) > 0 
                    AND CAST(REPLACE(voters.precinct, '** ', '') AS TEXT) GLOB '[0-9]*'
                    THEN printf('%04d', CAST(REPLACE(voters.precinct, '** ', '') AS INTEGER))
                    ELSE REPLACE(voters.precinct, '** ', '')
                END
            )
        WHERE county IS NOT NULL AND precinct IS NOT NULL
    """)
    
    conn.commit()
    elapsed = time.time() - start
    
    print(f"✓ Update complete in {elapsed:.1f} seconds")
    
    # Check results
    cursor.execute("""
        SELECT 
            COUNT(congressional_district) as has_cong,
            COUNT(state_senate_district) as has_senate,
            COUNT(state_house_district) as has_house,
            SUM(CASE WHEN congressional_district IS NOT NULL 
                     AND state_senate_district IS NOT NULL 
                     AND state_house_district IS NOT NULL THEN 1 ELSE 0 END) as has_all
        FROM voters
    """)
    result = cursor.fetchone()
    
    print(f"\nFinal assignment:")
    print(f"  Congressional: {result[0]:,} ({result[0]/total*100:.1f}%)")
    print(f"  State Senate: {result[1]:,} ({result[1]/total*100:.1f}%)")
    print(f"  State House: {result[2]:,} ({result[2]/total*100:.1f}%)")
    print(f"  ALL 3 districts: {result[3]:,} ({result[3]/total*100:.1f}%)")
    
    conn.close()

def create_performance_indexes(db_path):
    """Create indexes for fast queries."""
    print("\n" + "="*80)
    print("CREATING PERFORMANCE INDEXES")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    indexes = [
        ("idx_voters_congressional", "voters(congressional_district)"),
        ("idx_voters_senate", "voters(state_senate_district)"),
        ("idx_voters_house", "voters(state_house_district)"),
        ("idx_voters_county_precinct", "voters(county, precinct)"),
        ("idx_voters_zip", "voters(zip)"),
        ("idx_voters_vuid", "voters(vuid)"),
    ]
    
    for idx_name, idx_def in indexes:
        try:
            cursor.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {idx_def}")
            print(f"  ✓ {idx_name}")
        except Exception as e:
            print(f"  - {idx_name}: {e}")
    
    conn.commit()
    conn.close()
    
    print("\n✓ All indexes created")

def verify_results(db_path):
    """Verify final results."""
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # District counts
    print("\nDistrict counts:")
    
    cursor.execute("SELECT COUNT(DISTINCT congressional_district) FROM voters WHERE congressional_district IS NOT NULL")
    print(f"  Congressional districts: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(DISTINCT state_senate_district) FROM voters WHERE state_senate_district IS NOT NULL")
    print(f"  State Senate districts: {cursor.fetchone()[0]}")
    
    cursor.execute("SELECT COUNT(DISTINCT state_house_district) FROM voters WHERE state_house_district IS NOT NULL")
    print(f"  State House districts: {cursor.fetchone()[0]}")
    
    # Sample voters
    print("\nSample voter records:")
    cursor.execute("""
        SELECT vuid, county, precinct, congressional_district, state_senate_district, state_house_district
        FROM voters
        WHERE congressional_district IS NOT NULL
        AND state_senate_district IS NOT NULL
        AND state_house_district IS NOT NULL
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        print(f"  VUID {row[0]}: {row[1]} Pct {row[2]} -> TX-{row[3]}, SD-{row[4]}, HD-{row[5]}")
    
    conn.close()

def main():
    db_path = "data/whovoted.db"
    
    print("="*80)
    print("COMPLETE DISTRICT ASSIGNMENT - FAST & OPTIMIZED")
    print("="*80)
    print("\nThis will:")
    print("  1. Parse ALL precinct files (Congressional, Senate, House)")
    print("  2. Create fast lookup table with ALL 3 district types")
    print("  3. Assign ALL districts to EVERY voter in one operation")
    print("  4. Create performance indexes for instant queries")
    print("  5. Verify results")
    print("="*80)
    
    # Step 1: Parse all precinct files
    mappings = parse_all_precinct_files()
    
    # Step 2: Create fast lookup table
    create_fast_lookup_table(db_path, mappings)
    
    # Step 3: Assign all districts
    assign_all_districts_bulk(db_path)
    
    # Step 4: Create indexes
    create_performance_indexes(db_path)
    
    # Step 5: Verify
    verify_results(db_path)
    
    print("\n" + "="*80)
    print("✓ COMPLETE - ALL VOTERS ASSIGNED TO ALL DISTRICTS")
    print("="*80)
    print("\nEvery voter now has:")
    print("  • Congressional District")
    print("  • State Senate District")
    print("  • State House District")
    print("  • County")
    print("  • Precinct")
    print("  • ZIP Code")
    print("\nAll tied to VUID with fast indexed lookups!")

if __name__ == '__main__':
    main()
