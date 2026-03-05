#!/usr/bin/env python3
"""Check current 2026 data breakdown"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    print('2026 Primary Data Breakdown:')
    print('=' * 50)
    
    # By voting method
    rows = conn.execute('''
        SELECT voting_method, party_voted, COUNT(*) as cnt
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        GROUP BY voting_method, party_voted
        ORDER BY voting_method, party_voted
    ''').fetchall()
    
    for r in rows:
        print(f'{r[0]:20} {r[1]:15} {r[2]:,}')
    
    print()
    print('Total by party (unique voters):')
    rows = conn.execute('''
        SELECT party_voted, COUNT(DISTINCT vuid) as cnt
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        GROUP BY party_voted
    ''').fetchall()
    
    for r in rows:
        print(f'{r[0]:15} {r[1]:,}')
