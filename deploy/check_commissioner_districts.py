#!/usr/bin/env python3
import sqlite3
import sys

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# Check if commissioner_district column exists
cursor = conn.execute("PRAGMA table_info(voters)")
columns = [row[1] for row in cursor.fetchall()]
print(f"Columns in voters table: {', '.join(columns)}")
print()

if 'commissioner_district' in columns:
    # Get distinct commissioner districts
    cursor = conn.execute("""
        SELECT DISTINCT commissioner_district 
        FROM voters 
        WHERE commissioner_district IS NOT NULL 
        ORDER BY commissioner_district 
        LIMIT 20
    """)
    districts = [row[0] for row in cursor.fetchall()]
    print(f"Commissioner Districts found: {districts}")
    
    # Count voters with commissioner district
    cursor = conn.execute("""
        SELECT COUNT(*) 
        FROM voters 
        WHERE commissioner_district IS NOT NULL
    """)
    count = cursor.fetchone()[0]
    print(f"Voters with commissioner district: {count:,}")
    
    # Check Hidalgo County specifically
    cursor = conn.execute("""
        SELECT commissioner_district, COUNT(*) as count
        FROM voters 
        WHERE county = 'Hidalgo' AND commissioner_district IS NOT NULL
        GROUP BY commissioner_district
        ORDER BY commissioner_district
    """)
    hidalgo_districts = cursor.fetchall()
    print(f"\nHidalgo County Commissioner Districts:")
    for district, count in hidalgo_districts:
        print(f"  {district}: {count:,} voters")
else:
    print("commissioner_district column does NOT exist in voters table")

conn.close()
