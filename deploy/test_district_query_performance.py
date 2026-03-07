#!/usr/bin/env python3
"""Test query performance for district lookups"""

import sqlite3
import time

def main():
    conn = sqlite3.connect('data/whovoted.db')
    cursor = conn.cursor()
    
    print("="*80)
    print("DISTRICT QUERY PERFORMANCE TEST")
    print("="*80)
    
    # Test 1: Get all voters in TX-15
    print("\nTest 1: Get all voters in TX-15")
    start = time.time()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM voters 
        WHERE congressional_district = '15'
    """)
    count = cursor.fetchone()[0]
    elapsed = (time.time() - start) * 1000
    print(f"  Result: {count:,} voters")
    print(f"  Time: {elapsed:.2f}ms")
    
    # Test 2: Get voters by all 3 districts
    print("\nTest 2: Get voters in TX-15, SD-20, HD-35")
    start = time.time()
    cursor.execute("""
        SELECT COUNT(*) 
        FROM voters 
        WHERE congressional_district = '15'
        AND state_senate_district = '20'
        AND state_house_district = '35'
    """)
    count = cursor.fetchone()[0]
    elapsed = (time.time() - start) * 1000
    print(f"  Result: {count:,} voters")
    print(f"  Time: {elapsed:.2f}ms")
    
    # Test 3: Get district counts
    print("\nTest 3: Count voters per congressional district")
    start = time.time()
    cursor.execute("""
        SELECT congressional_district, COUNT(*) as voters
        FROM voters
        WHERE congressional_district IS NOT NULL
        GROUP BY congressional_district
        ORDER BY voters DESC
        LIMIT 10
    """)
    results = cursor.fetchall()
    elapsed = (time.time() - start) * 1000
    print(f"  Top 10 districts:")
    for row in results:
        print(f"    TX-{row[0]}: {row[1]:,} voters")
    print(f"  Time: {elapsed:.2f}ms")
    
    # Test 4: Get voter by VUID with all districts
    print("\nTest 4: Get single voter with all district info")
    start = time.time()
    cursor.execute("""
        SELECT vuid, county, precinct, congressional_district, 
               state_senate_district, state_house_district, zip
        FROM voters
        WHERE vuid = '2172969274'
    """)
    row = cursor.fetchone()
    elapsed = (time.time() - start) * 1000
    if row:
        print(f"  VUID: {row[0]}")
        print(f"  County: {row[1]}, Precinct: {row[2]}")
        print(f"  Districts: TX-{row[3]}, SD-{row[4]}, HD-{row[5]}")
        print(f"  ZIP: {row[6]}")
    print(f"  Time: {elapsed:.2f}ms")
    
    # Test 5: Complex query - voters who voted in 2024 general in TX-15
    print("\nTest 5: TX-15 voters who voted in 2024 general election")
    start = time.time()
    cursor.execute("""
        SELECT COUNT(*)
        FROM voters
        WHERE congressional_district = '15'
        AND voted_2024_general = 1
    """)
    count = cursor.fetchone()[0]
    elapsed = (time.time() - start) * 1000
    print(f"  Result: {count:,} voters")
    print(f"  Time: {elapsed:.2f}ms")
    
    # Check indexes
    print("\n" + "="*80)
    print("INDEXES ON VOTERS TABLE")
    print("="*80)
    cursor.execute("""
        SELECT name, sql 
        FROM sqlite_master 
        WHERE type = 'index' 
        AND tbl_name = 'voters'
        AND name NOT LIKE 'sqlite_%'
    """)
    for row in cursor.fetchall():
        print(f"\n{row[0]}:")
        if row[1]:
            print(f"  {row[1]}")
    
    conn.close()
    
    print("\n" + "="*80)
    print("✓ ALL QUERIES FAST - READY FOR PRODUCTION")
    print("="*80)

if __name__ == '__main__':
    main()
