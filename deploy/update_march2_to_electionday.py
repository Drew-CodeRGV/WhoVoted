#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    # Update the records from 2026-03-02 with NULL source_file and early-voting method
    count = conn.execute('''
        UPDATE voter_elections 
        SET voting_method = 'election-day'
        WHERE DATE(created_at) = '2026-03-02'
        AND source_file IS NULL
        AND voting_method = 'early-voting'
    ''').rowcount
    conn.commit()
    
    print(f'Updated {count:,} records to election-day')
    
    # Show breakdown
    rows = conn.execute('''
        SELECT voting_method, COUNT(*) as cnt
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        GROUP BY voting_method
    ''').fetchall()
    
    print('\n2026 breakdown:')
    for r in rows:
        print(f'  {r[0]:20} {r[1]:,}')
    
    # Clear cache
    from app import cache_invalidate
    cache_invalidate()
    print('\nCache cleared!')
