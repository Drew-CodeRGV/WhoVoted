#!/usr/bin/env python3
"""
Fix the voting methods correctly:
1. Change the 61,535 records from March 2nd BACK to early-voting (they were early vote data)
2. The election day data you uploaded today should be separate
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    print('Fixing voting methods...')
    print('=' * 60)
    
    # Step 1: Change the March 2nd records BACK to early-voting
    print('\nStep 1: Reverting March 2nd records back to early-voting...')
    count1 = conn.execute('''
        UPDATE voter_elections 
        SET voting_method = 'early-voting'
        WHERE DATE(created_at) = '2026-03-02'
        AND source_file IS NULL
        AND voting_method = 'election-day'
        AND election_date = '2026-03-03'
    ''').rowcount
    print(f'  Reverted {count1:,} records back to early-voting')
    
    conn.commit()
    
    # Show current state for Hidalgo
    print('\nCurrent Hidalgo County 2026 data:')
    rows = conn.execute('''
        SELECT ve.voting_method, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        GROUP BY ve.voting_method
        ORDER BY ve.voting_method
    ''').fetchall()
    
    for r in rows:
        print(f'  {r[0]:20} {r[1]:>10,}')
    
    print('\nThe election day data you uploaded (16,857 + 6,172 = 23,029) ')
    print('needs to be identified and tagged as election-day.')
    print('Can you tell me which files or when you uploaded them?')
    
    # Clear cache
    from app import cache_invalidate
    cache_invalidate()
    print('\nCache cleared!')
