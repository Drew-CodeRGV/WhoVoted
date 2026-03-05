#!/usr/bin/env python3
"""
Fix 2026 election day data that was incorrectly tagged as early-voting.

The user uploaded election day data but selected "early-voting" in the form.
This script identifies and corrects those records.
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

print('Analyzing 2026 data...')
print('=' * 60)

with db.get_db() as conn:
    # Check current state
    print('\nCurrent 2026 data:')
    rows = conn.execute('''
        SELECT voting_method, COUNT(*) as cnt, MIN(created_at) as first, MAX(created_at) as last
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        GROUP BY voting_method
        ORDER BY voting_method
    ''').fetchall()
    
    for r in rows:
        print(f'  {r[0]:20} {r[1]:>10,} voters  (first: {r[2]}, last: {r[3]})')
    
    # The election day data was likely uploaded most recently
    # Let's check the most recent upload
    print('\nMost recent uploads:')
    recent = conn.execute('''
        SELECT voting_method, COUNT(*) as cnt, created_at
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        GROUP BY voting_method, created_at
        ORDER BY created_at DESC
        LIMIT 5
    ''').fetchall()
    
    for r in recent:
        print(f'  {r[2]}: {r[0]:20} {r[1]:>10,} voters')
    
    # Ask user to confirm which records to update
    print('\n' + '=' * 60)
    print('The most recent upload appears to be election day data')
    print('that was incorrectly tagged as early-voting.')
    print('\nWould you like to:')
    print('1. Update ALL early-voting records to election-day')
    print('2. Update only the most recent batch')
    print('3. Cancel (do nothing)')
    
    choice = input('\nEnter choice (1/2/3): ').strip()
    
    if choice == '1':
        # Update all early-voting to election-day
        count = conn.execute('''
            UPDATE voter_elections 
            SET voting_method = 'election-day'
            WHERE election_date = '2026-03-03' 
            AND voting_method = 'early-voting'
        ''').rowcount
        conn.commit()
        print(f'\n✓ Updated {count:,} records to election-day')
        
    elif choice == '2':
        # Get the most recent created_at timestamp for early-voting
        latest = conn.execute('''
            SELECT MAX(created_at) FROM voter_elections
            WHERE election_date = '2026-03-03' AND voting_method = 'early-voting'
        ''').fetchone()[0]
        
        if latest:
            count = conn.execute('''
                UPDATE voter_elections 
                SET voting_method = 'election-day'
                WHERE election_date = '2026-03-03' 
                AND voting_method = 'early-voting'
                AND created_at = ?
            ''', (latest,)).rowcount
            conn.commit()
            print(f'\n✓ Updated {count:,} records from {latest} to election-day')
        else:
            print('\nNo records found to update')
    else:
        print('\nCancelled - no changes made')
    
    # Show final state
    print('\nFinal 2026 data:')
    rows = conn.execute('''
        SELECT voting_method, COUNT(*) as cnt
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        GROUP BY voting_method
        ORDER BY voting_method
    ''').fetchall()
    
    for r in rows:
        print(f'  {r[0]:20} {r[1]:>10,} voters')
