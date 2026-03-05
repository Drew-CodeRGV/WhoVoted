#!/usr/bin/env python3
"""
Revert Hidalgo County 2026 voting methods back to early-voting.

SITUATION:
- We accidentally changed 61,527 early voting records to "election-day"
- The actual election day data (23,029 voters) was uploaded separately but can't be distinguished
- Solution: Revert ALL election-day records back to early-voting
- User will re-upload the election day data with correct method selected

This will result in:
- Early Voting: 61,527 records
- Mail-In: 1,341 records
- Election Day: 0 records (until user re-uploads)
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    print('Hidalgo County 2026 - Reverting to Early Voting')
    print('=' * 80)
    
    # Show current state
    print('\nCURRENT STATE:')
    rows = conn.execute('''
        SELECT ve.voting_method, ve.party_voted, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        GROUP BY ve.voting_method, ve.party_voted
        ORDER BY ve.voting_method, ve.party_voted
    ''').fetchall()
    
    for r in rows:
        print(f'  {r[0]:<20} {r[1]:<15} {r[2]:>10,}')
    
    # Show totals
    print('\nTOTALS BY METHOD:')
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
        print(f'  {r[0]:<20} {r[1]:>10,}')
    
    # Apply the fix
    print('\n' + '=' * 80)
    print('APPLYING FIX: Changing all election-day records to early-voting...')
    
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
    print(f'Changed {count:,} records from election-day to early-voting')
    
    # Show new state
    print('\nNEW STATE:')
    rows3 = conn.execute('''
        SELECT ve.voting_method, ve.party_voted, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        GROUP BY ve.voting_method, ve.party_voted
        ORDER BY ve.voting_method, ve.party_voted
    ''').fetchall()
    
    for r in rows3:
        print(f'  {r[0]:<20} {r[1]:<15} {r[2]:>10,}')
    
    print('\nTOTALS BY METHOD:')
    rows4 = conn.execute('''
        SELECT ve.voting_method, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        GROUP BY ve.voting_method
        ORDER BY ve.voting_method
    ''').fetchall()
    
    for r in rows4:
        print(f'  {r[0]:<20} {r[1]:>10,}')
    
    # Clear cache
    print('\nClearing API cache...')
    from app import cache_invalidate
    cache_invalidate()
    print('Cache cleared!')
    
    print('\n' + '=' * 80)
    print('FIX COMPLETE!')
    print('\nNEXT STEPS FOR USER:')
    print('1. Go to the upload page')
    print('2. Upload your election day CSV files:')
    print('   - ED12026R25Hidalgo County - 2026 Primary - Republican.csv')
    print('   - ED12026P25Hidalgo County - 2026 Primary - Democratic.csv')
    print('3. Make sure to select "Election Day" in the voting method dropdown')
    print('4. After upload, you should see:')
    print('   - Early Voting: ~61,527')
    print('   - Election Day: ~23,029')
    print('   - Mail-In: 1,341')
    print('   - Complete Election (combined): ~85,897')
    print('=' * 80)
