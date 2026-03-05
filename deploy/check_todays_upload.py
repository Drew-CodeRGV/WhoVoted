#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    # Check all uploads from March 2nd (when the NULL source_file records were created)
    print('Checking uploads from 2026-03-02:')
    print('=' * 60)
    
    rows = conn.execute('''
        SELECT 
            source_file,
            voting_method,
            party_voted,
            COUNT(*) as cnt,
            MIN(created_at) as first,
            MAX(created_at) as last
        FROM voter_elections
        WHERE DATE(created_at) = '2026-03-02'
        GROUP BY source_file, voting_method, party_voted
        ORDER BY first
    ''').fetchall()
    
    if not rows:
        print('No uploads found from 2026-03-02')
    else:
        for r in rows:
            print(f'\nFile: {r[0] or "NULL"}')
            print(f'  Method: {r[1]}')
            print(f'  Party: {r[2]}')
            print(f'  Count: {r[3]:,}')
            print(f'  Time: {r[4]} to {r[5]}')
