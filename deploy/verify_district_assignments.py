#!/usr/bin/env python3
"""Verify district assignments after running assign_all_voters_all_districts_now.py"""

import sqlite3

def main():
    conn = sqlite3.connect('data/whovoted.db')
    cursor = conn.cursor()

    print('\n=== CONGRESSIONAL DISTRICTS WITH VOTERS ===')
    cursor.execute('''
        SELECT congressional_district, COUNT(*) as voters
        FROM voters
        WHERE congressional_district IS NOT NULL
        GROUP BY congressional_district
        ORDER BY CAST(congressional_district AS INTEGER)
    ''')
    for row in cursor.fetchall():
        print(f'TX-{row[0]}: {row[1]:,} voters')

    print('\n=== STATE SENATE DISTRICTS WITH VOTERS ===')
    cursor.execute('''
        SELECT state_senate_district, COUNT(*) as voters
        FROM voters
        WHERE state_senate_district IS NOT NULL
        GROUP BY state_senate_district
        ORDER BY CAST(state_senate_district AS INTEGER)
    ''')
    for row in cursor.fetchall():
        print(f'SD-{row[0]}: {row[1]:,} voters')

    print('\n=== STATE HOUSE DISTRICTS WITH VOTERS (Top 20) ===')
    cursor.execute('''
        SELECT state_house_district, COUNT(*) as voters
        FROM voters
        WHERE state_house_district IS NOT NULL
        GROUP BY state_house_district
        ORDER BY voters DESC
        LIMIT 20
    ''')
    for row in cursor.fetchall():
        print(f'HD-{row[0]}: {row[1]:,} voters')

    print('\n=== VOTERS WITHOUT DISTRICTS ===')
    cursor.execute('''
        SELECT COUNT(*) as total,
               COUNT(CASE WHEN county IS NULL THEN 1 END) as no_county,
               COUNT(CASE WHEN precinct IS NULL THEN 1 END) as no_precinct
        FROM voters
        WHERE congressional_district IS NULL
           OR state_senate_district IS NULL
           OR state_house_district IS NULL
    ''')
    row = cursor.fetchone()
    print(f'Total without all districts: {row[0]:,}')
    print(f'Missing county: {row[1]:,}')
    print(f'Missing precinct: {row[2]:,}')

    print('\n=== SAMPLE VOTERS WITHOUT DISTRICTS ===')
    cursor.execute('''
        SELECT vuid, county, precinct, congressional_district, state_senate_district, state_house_district
        FROM voters
        WHERE congressional_district IS NULL
           OR state_senate_district IS NULL
           OR state_house_district IS NULL
        LIMIT 10
    ''')
    print('VUID | County | Precinct | Cong | Senate | House')
    print('-' * 70)
    for row in cursor.fetchall():
        print(f'{row[0]} | {row[1]} | {row[2]} | {row[3]} | {row[4]} | {row[5]}')

    conn.close()

if __name__ == '__main__':
    main()
