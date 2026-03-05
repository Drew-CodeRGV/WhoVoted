#!/usr/bin/env python3
"""
Fix Hidalgo County 2026 voting methods.

CURRENT STATE:
- 61,527 records marked as "election-day" (but user says these are early voting)
- 1,341 records marked as "mail-in" (correct)
- User uploaded election day data (16,857 + 6,172 = 23,029) but can't find it

PROBLEM:
All records from March 2nd have source_file = NULL, making it hard to distinguish
between early voting and election day uploads.

SOLUTION:
Since we can't distinguish the uploads by file or timestamp, we need the user to
tell us which specific records are election day vs early voting.

For now, let's revert ALL the election-day records back to early-voting,
and the user can re-upload the election day data with the correct method selected.
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    print('Hidalgo County 2026 - Fixing Voting Methods')
    print('=' * 80)
    
    # Show current state
    print('\nCURRENT STATE:')
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
        print(f'  {r[0]:<20} {r[1]:>10,}')
    
    # Ask for confirmation
    print('\n' + '=' * 80)
    print('PROPOSED FIX:')
    print('  Change all 61,527 "election-day" records to "early-voting"')
    print('  Keep 1,341 "mail-in" records as-is')
    print('\nAfter this fix, you will need to:')
    print('  1. Re-upload the election day data files')
    print('  2. Make sure "Election Day" is selected in the upload form')
    print('=' * 80)
    
    response = input('\nProceed with fix? (yes/no): ')
    
    if response.lower() != 'yes':
        print('Aborted.')
        sys.exit(0)
    
    # Apply the fix
    print('\nApplying fix...')
    count = conn.execute('''
        UPDATE voter_elections 
        SET voting_method = 'early-voting'
        WHERE vuid IN (
            SELECT ve.vuid
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = '2026-03-03'
            AND v.county = 'Hidalgo'
            AND ve.voting_method = 'election-day'
        )
        AND election_date = '2026-03-03'
        AND voting_method = 'election-day'
    ''').rowcount
    
    conn.commit()
    print(f'  Changed {count:,} records from election-day to early-voting')
    
    # Show new state
    print('\nNEW STATE:')
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
        print(f'  {r[0]:<20} {r[1]:>10,}')
    
    # Clear cache
    print('\nClearing API cache...')
    from app import cache_invalidate
    cache_invalidate()
    print('Done!')
    
    print('\n' + '=' * 80)
    print('NEXT STEPS:')
    print('1. Re-upload your election day CSV files')
    print('2. Select "Election Day" in the voting method dropdown')
    print('3. The system will then show:')
    print('   - Early Voting: ~61,527')
    print('   - Election Day: ~23,029')
    print('   - Mail-In: 1,341')
    print('   - Combined: ~85,897')
    print('=' * 80)
