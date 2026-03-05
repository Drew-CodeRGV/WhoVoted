#!/usr/bin/env python3
"""Check if 2026 election day data exists"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    print('2026 Election Data Breakdown:')
    print('=' * 60)
    
    rows = conn.execute('''
        SELECT voting_method, party_voted, COUNT(*) as cnt
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        GROUP BY voting_method, party_voted
        ORDER BY voting_method, party_voted
    ''').fetchall()
    
    if not rows:
        print('NO DATA FOUND for 2026-03-03')
    else:
        for r in rows:
            print(f'{r[0]:20} {r[1]:15} {r[2]:,}')
    
    print()
    print('Total unique voters:')
    total = conn.execute('''
        SELECT COUNT(DISTINCT vuid) FROM voter_elections
        WHERE election_date = '2026-03-03'
    ''').fetchone()[0]
    print(f'{total:,}')
