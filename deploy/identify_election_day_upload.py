#!/usr/bin/env python3
"""
Identify the actual election day upload from today.
The user uploaded 2 files: 16,857 + 6,172 = 23,029 voters
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    print('Analyzing all uploads from March 2-5, 2026:')
    print('=' * 60)
    
    # Check uploads from the last few days
    rows = conn.execute('''
        SELECT 
            DATE(created_at) as upload_date,
            source_file,
            voting_method,
            party_voted,
            COUNT(*) as cnt,
            MIN(created_at) as first,
            MAX(created_at) as last
        FROM voter_elections
        WHERE DATE(created_at) >= '2026-03-02'
        AND election_date = '2026-03-03'
        GROUP BY DATE(created_at), source_file, voting_method, party_voted
        ORDER BY first
    ''').fetchall()
    
    if not rows:
        print('No uploads found')
    else:
        for r in rows:
            print(f'\nDate: {r[0]}')
            print(f'  File: {r[1] or "NULL"}')
            print(f'  Method: {r[2]}')
            print(f'  Party: {r[3]}')
            print(f'  Count: {r[4]:,}')
            print(f'  Time: {r[5]} to {r[6]}')
    
    # Look for uploads that match the expected counts (16,857 or 6,172)
    print('\n\nLooking for uploads matching election day counts (16,857 or 6,172):')
    print('=' * 60)
    
    rows2 = conn.execute('''
        SELECT 
            DATE(created_at) as upload_date,
            TIME(created_at) as upload_time,
            source_file,
            voting_method,
            party_voted,
            COUNT(*) as cnt
        FROM voter_elections
        WHERE DATE(created_at) >= '2026-03-02'
        AND election_date = '2026-03-03'
        GROUP BY DATE(created_at), TIME(created_at), source_file, voting_method, party_voted
        HAVING cnt IN (16857, 6172, 23029)
        ORDER BY upload_date, upload_time
    ''').fetchall()
    
    if rows2:
        for r in rows2:
            print(f'\nDate: {r[0]} {r[1]}')
            print(f'  File: {r[2] or "NULL"}')
            print(f'  Method: {r[3]}')
            print(f'  Party: {r[4]}')
            print(f'  Count: {r[5]:,}')
    else:
        print('No exact matches found. Showing all uploads by time:')
        
        rows3 = conn.execute('''
            SELECT 
                created_at,
                source_file,
                voting_method,
                party_voted,
                COUNT(*) as cnt
            FROM voter_elections
            WHERE DATE(created_at) >= '2026-03-02'
            AND election_date = '2026-03-03'
            GROUP BY created_at, source_file, voting_method, party_voted
            ORDER BY created_at
        ''').fetchall()
        
        for r in rows3:
            print(f'{r[0]}: {r[1] or "NULL":30} {r[2]:15} {r[3]:15} {r[4]:>10,}')
