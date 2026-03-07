#!/usr/bin/env python3
"""
Check if House and Senate reference data exists in precinct_districts table
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("=" * 80)
    print("CHECKING HOUSE AND SENATE REFERENCE DATA")
    print("=" * 80)
    
    # Check if precinct_districts table exists
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='precinct_districts'
    """)
    
    if not cursor.fetchone():
        print("\n❌ precinct_districts table does NOT exist")
        print("\nNeed to run: python deploy/parse_vtd_correctly.py")
        conn.close()
        return
    
    print("\n✓ precinct_districts table exists")
    
    # Check columns
    cursor.execute("PRAGMA table_info(precinct_districts)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"\nColumns: {', '.join(columns)}")
    
    # Check total records
    cursor.execute("SELECT COUNT(*) FROM precinct_districts")
    total = cursor.fetchone()[0]
    print(f"\nTotal precinct mappings: {total:,}")
    
    # Check Congressional districts
    cursor.execute("""
        SELECT COUNT(*) FROM precinct_districts 
        WHERE congressional_district IS NOT NULL
    """)
    cong_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT congressional_district) FROM precinct_districts 
        WHERE congressional_district IS NOT NULL
    """)
    cong_districts = cursor.fetchone()[0]
    
    print(f"\nCongressional Districts:")
    print(f"  Precincts with data: {cong_count:,}")
    print(f"  Unique districts: {cong_districts}")
    
    # Check State Senate districts
    cursor.execute("""
        SELECT COUNT(*) FROM precinct_districts 
        WHERE state_senate_district IS NOT NULL
    """)
    senate_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT state_senate_district) FROM precinct_districts 
        WHERE state_senate_district IS NOT NULL
    """)
    senate_districts = cursor.fetchone()[0]
    
    print(f"\nState Senate Districts:")
    print(f"  Precincts with data: {senate_count:,}")
    print(f"  Unique districts: {senate_districts}")
    
    # Check State House districts
    cursor.execute("""
        SELECT COUNT(*) FROM precinct_districts 
        WHERE state_house_district IS NOT NULL
    """)
    house_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT state_house_district) FROM precinct_districts 
        WHERE state_house_district IS NOT NULL
    """)
    house_districts = cursor.fetchone()[0]
    
    print(f"\nState House Districts:")
    print(f"  Precincts with data: {house_count:,}")
    print(f"  Unique districts: {house_districts}")
    
    # Check precinct_normalized table
    print("\n" + "=" * 80)
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name='precinct_normalized'
    """)
    
    if not cursor.fetchone():
        print("❌ precinct_normalized table does NOT exist")
        print("\nNeed to run: python deploy/build_normalized_precinct_system.py")
    else:
        print("✓ precinct_normalized table exists")
        
        cursor.execute("SELECT COUNT(*) FROM precinct_normalized")
        norm_total = cursor.fetchone()[0]
        print(f"  Total normalized mappings: {norm_total:,}")
        
        # Check if it has House/Senate data
        cursor.execute("""
            SELECT COUNT(*) FROM precinct_normalized 
            WHERE state_house_district IS NOT NULL
        """)
        norm_house = cursor.fetchone()[0]
        
        cursor.execute("""
            SELECT COUNT(*) FROM precinct_normalized 
            WHERE state_senate_district IS NOT NULL
        """)
        norm_senate = cursor.fetchone()[0]
        
        print(f"  With House districts: {norm_house:,}")
        print(f"  With Senate districts: {norm_senate:,}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if house_count == 0 or senate_count == 0:
        print("\n❌ MISSING REFERENCE DATA")
        print("\nThe VTD files need to be parsed to populate House and Senate districts.")
        print("\nRun this command:")
        print("  python deploy/parse_vtd_correctly.py")
    elif house_districts < 100 or senate_districts < 20:
        print("\n⚠ INCOMPLETE REFERENCE DATA")
        print(f"\nExpected ~150 House districts, found {house_districts}")
        print(f"Expected ~31 Senate districts, found {senate_districts}")
        print("\nRe-run: python deploy/parse_vtd_correctly.py")
    else:
        print("\n✓ REFERENCE DATA LOOKS GOOD")
        print("\nNext step: Build normalized precinct system")
        print("  python deploy/build_normalized_precinct_system.py")
    
    conn.close()

if __name__ == '__main__':
    main()
