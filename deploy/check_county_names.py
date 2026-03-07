#!/usr/bin/env python3
"""Check county name formatting in JSON files vs database"""

import json
import sqlite3

def main():
    # Load county names from JSON
    with open('data/district_reference/congressional_counties.json') as f:
        data = json.load(f)
    
    all_counties = set()
    for district_info in data.values():
        all_counties.update(district_info['counties'])
    
    print('=== COUNTIES WITH "Mc", "De", or "La" IN JSON FILES ===')
    problem_counties = sorted([c for c in all_counties if 'Mc' in c or 'De' in c or 'La' in c])
    for county in problem_counties:
        print(f'  {county}')
    
    # Check database
    conn = sqlite3.connect('data/whovoted.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT county
        FROM voters
        WHERE county LIKE '%Mc%' OR county LIKE '%De%' OR county LIKE '%La%'
        ORDER BY county
    ''')
    
    print('\n=== COUNTIES WITH "Mc", "De", or "La" IN DATABASE ===')
    db_counties = []
    for row in cursor.fetchall():
        print(f'  {row[0]}')
        db_counties.append(row[0])
    
    print('\n=== CASE MISMATCH ANALYSIS ===')
    for db_county in db_counties:
        matches = [j for j in problem_counties if j.lower() == db_county.lower()]
        if matches:
            if matches[0] != db_county:
                print(f'MISMATCH: DB has "{db_county}" but JSON has "{matches[0]}"')
        else:
            print(f'NOT FOUND: DB has "{db_county}" but not in JSON')
    
    conn.close()

if __name__ == '__main__':
    main()
