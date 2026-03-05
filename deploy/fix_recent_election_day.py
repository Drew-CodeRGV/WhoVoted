#!/usr/bin/env python3
"""
Fix the two files just uploaded - change them from early-voting to election-day.
The files have source_file = NULL and were uploaded today.
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db
from datetime import datetime, timedelta

print('Fixing election day files uploaded today...')
print('=' * 60)

with db.get_db() as conn:
    # Find records with NULL source_file from today
    today = datetime.now().date().isoformat()
    
    count_check = conn.execute('''
        SELECT COUNT(*), MIN(created_at), MAX(created_at)
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        AND source_file IS NULL
        AND DATE(created_at) = ?
    ''', (today,)).fetchone()
    
    if count_check[0] == 0:
        print(f'No records found with NULL source_file from today ({today})')
        sys.exit(0)
    
    print(f'\nFound {count_check[0]:,} records uploaded today')
    print(f'  First: {count_check[1]}')
    print(f'  Last: {count_check[2]}')
    
    # Update to election-day
    print('\nUpdating voting_method to election-day...')
    count = conn.execute('''
        UPDATE voter_elections 
        SET voting_method = 'election-day'
        WHERE election_date = '2026-03-03' 
        AND source_file IS NULL
        AND DATE(created_at) = ?
    ''', (today,)).rowcount
    
    conn.commit()
    
    print(f'✓ Updated {count:,} records')
    
    # Show final breakdown
    print('\nFinal 2026 data breakdown:')
    rows = conn.execute('''
        SELECT voting_method, COUNT(*) as cnt
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        GROUP BY voting_method
        ORDER BY voting_method
    ''').fetchall()
    
    for r in rows:
        print(f'  {r[0]:20} {r[1]:>10,} voters')
    
    print('\n✓ Done! Clearing API cache...')
    
    # Clear cache
    from app import cache_invalidate
    cache_invalidate()
    print('✓ Cache cleared!')
