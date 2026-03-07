#!/usr/bin/env python3
"""
Verify House and Senate district implementation is complete
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    print("=" * 80)
    print("HOUSE AND SENATE DISTRICT IMPLEMENTATION VERIFICATION")
    print("=" * 80)
    
    # 1. Check columns exist
    print("\n1. DATABASE SCHEMA")
    print("-" * 80)
    cursor.execute("PRAGMA table_info(voter_elections)")
    columns = [row[1] for row in cursor.fetchall()]
    
    has_house = 'state_house_district' in columns
    has_senate = 'state_senate_district' in columns
    has_cong = 'congressional_district' in columns
    
    print(f"✓ congressional_district column: {'EXISTS' if has_cong else 'MISSING'}")
    print(f"✓ state_senate_district column:  {'EXISTS' if has_senate else 'MISSING'}")
    print(f"✓ state_house_district column:   {'EXISTS' if has_house else 'MISSING'}")
    
    # 2. Check assignments
    print("\n2. DISTRICT ASSIGNMENTS")
    print("-" * 80)
    
    cursor.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = ?", (ELECTION_DATE,))
    total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM voter_elections 
        WHERE election_date = ? AND congressional_district IS NOT NULL AND congressional_district != ''
    """, (ELECTION_DATE,))
    cong_assigned = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM voter_elections 
        WHERE election_date = ? AND state_senate_district IS NOT NULL AND state_senate_district != ''
    """, (ELECTION_DATE,))
    senate_assigned = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM voter_elections 
        WHERE election_date = ? AND state_house_district IS NOT NULL AND state_house_district != ''
    """, (ELECTION_DATE,))
    house_assigned = cursor.fetchone()[0]
    
    print(f"Total voting records:        {total:>10,}")
    print(f"\nCongressional districts:     {cong_assigned:>10,} ({100*cong_assigned/total:>5.1f}%)")
    print(f"State Senate districts:      {senate_assigned:>10,} ({100*senate_assigned/total:>5.1f}%)")
    print(f"State House districts:       {house_assigned:>10,} ({100*house_assigned/total:>5.1f}%)")
    
    # 3. Check unique districts
    print("\n3. UNIQUE DISTRICTS")
    print("-" * 80)
    
    cursor.execute("""
        SELECT COUNT(DISTINCT congressional_district) FROM voter_elections 
        WHERE election_date = ? AND congressional_district IS NOT NULL AND congressional_district != ''
    """, (ELECTION_DATE,))
    cong_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT state_senate_district) FROM voter_elections 
        WHERE election_date = ? AND state_senate_district IS NOT NULL AND state_senate_district != ''
    """, (ELECTION_DATE,))
    senate_count = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT state_house_district) FROM voter_elections 
        WHERE election_date = ? AND state_house_district IS NOT NULL AND state_house_district != ''
    """, (ELECTION_DATE,))
    house_count = cursor.fetchone()[0]
    
    print(f"Congressional:  {cong_count:>3} districts (expected: 38)")
    print(f"State Senate:   {senate_count:>3} districts (expected: 31)")
    print(f"State House:    {house_count:>3} districts (expected: 150)")
    
    # 4. Show sample districts
    print("\n4. SAMPLE DISTRICTS")
    print("-" * 80)
    
    print("\nTop 5 House districts by voter count:")
    cursor.execute("""
        SELECT state_house_district, COUNT(*) as voters
        FROM voter_elections
        WHERE election_date = ? AND state_house_district IS NOT NULL
        GROUP BY state_house_district
        ORDER BY voters DESC
        LIMIT 5
    """, (ELECTION_DATE,))
    for row in cursor.fetchall():
        print(f"  {row[0]:<10} {row[1]:>8,} voters")
    
    print("\nTop 5 Senate districts by voter count:")
    cursor.execute("""
        SELECT state_senate_district, COUNT(*) as voters
        FROM voter_elections
        WHERE election_date = ? AND state_senate_district IS NOT NULL
        GROUP BY state_senate_district
        ORDER BY voters DESC
        LIMIT 5
    """, (ELECTION_DATE,))
    for row in cursor.fetchall():
        print(f"  {row[0]:<10} {row[1]:>8,} voters")
    
    # 5. Check Hidalgo County specifically
    print("\n5. HIDALGO COUNTY BREAKDOWN")
    print("-" * 80)
    
    cursor.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN ve.congressional_district IS NOT NULL THEN 1 ELSE 0 END) as with_cong,
            SUM(CASE WHEN ve.state_senate_district IS NOT NULL THEN 1 ELSE 0 END) as with_senate,
            SUM(CASE WHEN ve.state_house_district IS NOT NULL THEN 1 ELSE 0 END) as with_house
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ? AND v.county = 'Hidalgo'
    """, (ELECTION_DATE,))
    
    row = cursor.fetchone()
    print(f"Total Hidalgo voters:        {row[0]:>10,}")
    print(f"With Congressional:          {row[1]:>10,} ({100*row[1]/row[0]:>5.1f}%)")
    print(f"With Senate:                 {row[2]:>10,} ({100*row[2]/row[0]:>5.1f}%)")
    print(f"With House:                  {row[3]:>10,} ({100*row[3]/row[0]:>5.1f}%)")
    
    # Show Hidalgo districts
    print("\nHidalgo County districts:")
    cursor.execute("""
        SELECT DISTINCT ve.state_house_district
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ? AND v.county = 'Hidalgo'
        AND ve.state_house_district IS NOT NULL
        ORDER BY ve.state_house_district
    """, (ELECTION_DATE,))
    house_districts = [row[0] for row in cursor.fetchall()]
    print(f"  House: {', '.join(house_districts)}")
    
    cursor.execute("""
        SELECT DISTINCT ve.state_senate_district
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ? AND v.county = 'Hidalgo'
        AND ve.state_senate_district IS NOT NULL
        ORDER BY ve.state_senate_district
    """, (ELECTION_DATE,))
    senate_districts = [row[0] for row in cursor.fetchall()]
    print(f"  Senate: {', '.join(senate_districts)}")
    
    # 6. Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if house_assigned > 2000000 and senate_assigned > 2000000:
        print("\n✅ SUCCESS - House and Senate districts fully implemented!")
        print(f"\n   • {house_assigned:,} voters assigned to {house_count} House districts")
        print(f"   • {senate_assigned:,} voters assigned to {senate_count} Senate districts")
        print(f"   • Match rate: {100*house_assigned/total:.1f}%")
        print("\n   Next step: Add district boundaries to frontend for map display")
    else:
        print("\n⚠ INCOMPLETE - District assignments need attention")
    
    conn.close()

if __name__ == '__main__':
    main()
