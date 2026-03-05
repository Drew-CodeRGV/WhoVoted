#!/usr/bin/env python3
"""
Quick check to verify the upload was tagged correctly.
Run this immediately after uploading the election day files.
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

print('=' * 80)
print('UPLOAD VERIFICATION - Hidalgo County 2026 Primary')
print('=' * 80)

with db.get_db() as conn:
    # Get current counts
    print('\nCurrent voting method breakdown:')
    rows = conn.execute('''
        SELECT ve.voting_method, ve.party_voted, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        GROUP BY ve.voting_method, ve.party_voted
        ORDER BY ve.voting_method, ve.party_voted
    ''').fetchall()
    
    totals = {}
    for r in rows:
        print(f'  {r[0]:<20} {r[1]:<15} {r[2]:>10,}')
        totals[r[0]] = totals.get(r[0], 0) + r[2]
    
    print('\nTotals by method:')
    for method, count in sorted(totals.items()):
        print(f'  {method:<20} {count:>10,}')
    
    print(f'\n  {"GRAND TOTAL":<20} {sum(totals.values()):>10,}')
    
    # Check if we have election day data
    print('\n' + '=' * 80)
    if 'election-day' in totals:
        ed_count = totals['election-day']
        if ed_count >= 23000 and ed_count <= 24000:
            print('✓ SUCCESS! Election day data detected with correct count!')
            print(f'✓ Found {ed_count:,} election-day records (expected ~23,029)')
        elif ed_count > 0:
            print(f'⚠ Election day data found but count is unexpected: {ed_count:,}')
            print('  Expected: ~23,029 records')
        else:
            print('⚠ Election day method exists but has 0 records')
    else:
        print('⚠ WARNING: No election-day records found!')
        print('⚠ This means the upload was tagged as something else')
        
        # Check if early-voting increased
        ev_count = totals.get('early-voting', 0)
        if ev_count > 61527:
            print(f'\n⚠ PROBLEM DETECTED!')
            print(f'⚠ Early voting count is {ev_count:,} (expected 61,527)')
            print(f'⚠ Difference: {ev_count - 61527:,} extra records')
            print('⚠ This suggests the upload form had "Early Voting" selected!')
            print('\n⚠ ACTION NEEDED:')
            print('  1. Check the upload form - was "Election Day" selected?')
            print('  2. The form might have auto-selected "Early Voting" by default')
            print('  3. You may need to delete these records and re-upload')
    
    # Show most recent uploads
    print('\n' + '=' * 80)
    print('Most recent uploads (last 10):')
    rows2 = conn.execute('''
        SELECT 
            ve.created_at,
            ve.voting_method,
            ve.party_voted,
            COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        GROUP BY ve.created_at, ve.voting_method, ve.party_voted
        ORDER BY ve.created_at DESC
        LIMIT 10
    ''').fetchall()
    
    for r in rows2:
        print(f'  {str(r[0]):<20} {r[1]:<20} {r[2]:<15} {r[3]:>10,}')
    
    print('=' * 80)
