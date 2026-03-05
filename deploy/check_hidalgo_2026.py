#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    print('Hidalgo County 2026 Primary Data:')
    print('=' * 60)
    
    rows = conn.execute('''
        SELECT ve.voting_method, ve.party_voted, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        GROUP BY ve.voting_method, ve.party_voted
        ORDER BY ve.voting_method, ve.party_voted
    ''').fetchall()
    
    if not rows:
        print('No Hidalgo County data found')
    else:
        total = 0
        for r in rows:
            print(f'{r[0]:20} {r[1]:15} {r[2]:>10,}')
            total += r[2]
        
        print(f'\n{"TOTAL":20} {"":15} {total:>10,}')
        
        # Show by method only
        print('\nBy voting method:')
        rows2 = conn.execute('''
            SELECT ve.voting_method, COUNT(*) as cnt
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = '2026-03-03'
            AND v.county = 'Hidalgo'
            GROUP BY ve.voting_method
            ORDER BY ve.voting_method
        ''').fetchall()
        
        for r in rows2:
            print(f'  {r[0]:20} {r[1]:>10,}')
