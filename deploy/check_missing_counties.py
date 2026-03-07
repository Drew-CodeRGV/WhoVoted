#!/usr/bin/env python3
"""Check which counties have voters but no district mappings"""

import sqlite3

def main():
    conn = sqlite3.connect('data/whovoted.db')
    cursor = conn.cursor()

    print('\n=== COUNTIES WITH VOTERS BUT NO DISTRICT ASSIGNMENTS ===')
    cursor.execute('''
        SELECT county, COUNT(*) as voters_without_districts
        FROM voters
        WHERE (congressional_district IS NULL
           OR state_senate_district IS NULL
           OR state_house_district IS NULL)
        AND county IS NOT NULL
        GROUP BY county
        ORDER BY voters_without_districts DESC
    ''')
    
    total_missing = 0
    for row in cursor.fetchall():
        print(f'{row[0]}: {row[1]:,} voters without districts')
        total_missing += row[1]
    
    print(f'\nTotal voters without districts: {total_missing:,}')
    
    print('\n=== CHECKING COUNTY LOOKUP TABLE ===')
    cursor.execute('''
        SELECT county, congressional_district, state_senate_district, state_house_district
        FROM county_district_lookup
        WHERE county IN ('Mclennan', 'Lasalle')
    ''')
    
    print('County | Congressional | Senate | House')
    print('-' * 60)
    for row in cursor.fetchall():
        print(f'{row[0]} | {row[1]} | {row[2]} | {row[3]}')
    
    if cursor.rowcount == 0:
        print('No entries found for Mclennan or Lasalle in lookup table!')
    
    print('\n=== ALL COUNTIES IN LOOKUP TABLE (sample) ===')
    cursor.execute('''
        SELECT county, congressional_district, state_senate_district, state_house_district
        FROM county_district_lookup
        LIMIT 10
    ''')
    
    print('County | Congressional | Senate | House')
    print('-' * 60)
    for row in cursor.fetchall():
        print(f'{row[0]} | {row[1]} | {row[2]} | {row[3]}')

    conn.close()

if __name__ == '__main__':
    main()
