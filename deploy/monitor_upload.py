#!/usr/bin/env python3
"""
Real-time upload monitor for Hidalgo County election day data.
Watches for new uploads and verifies voting_method is set correctly.
"""
import sys
import time
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

print('=' * 80)
print('UPLOAD MONITOR - Watching for Hidalgo County Election Day Upload')
print('=' * 80)
print('\nCurrent state BEFORE upload:')

with db.get_db() as conn:
    # Get baseline counts
    rows = conn.execute('''
        SELECT ve.voting_method, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        GROUP BY ve.voting_method
        ORDER BY ve.voting_method
    ''').fetchall()
    
    baseline = {}
    for r in rows:
        baseline[r[0]] = r[1]
        print(f'  {r[0]:<20} {r[1]:>10,}')
    
    print(f'\n{"TOTAL":<20} {sum(baseline.values()):>10,}')

print('\n' + '=' * 80)
print('Monitoring for new uploads... (Press Ctrl+C to stop)')
print('Expected: ~23,029 new records with voting_method = "election-day"')
print('=' * 80)

last_total = sum(baseline.values())
check_count = 0

try:
    while True:
        time.sleep(2)  # Check every 2 seconds
        check_count += 1
        
        with db.get_db() as conn:
            # Get current counts
            rows = conn.execute('''
                SELECT ve.voting_method, COUNT(*) as cnt
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE ve.election_date = '2026-03-03'
                AND v.county = 'Hidalgo'
                GROUP BY ve.voting_method
                ORDER BY ve.voting_method
            ''').fetchall()
            
            current = {}
            for r in rows:
                current[r[0]] = r[1]
            
            current_total = sum(current.values())
            
            # Check if anything changed
            if current_total != last_total:
                print(f'\n[{time.strftime("%H:%M:%S")}] CHANGE DETECTED!')
                print('=' * 80)
                
                # Show what changed
                for method in set(list(baseline.keys()) + list(current.keys())):
                    old_count = baseline.get(method, 0)
                    new_count = current.get(method, 0)
                    diff = new_count - old_count
                    
                    if diff != 0:
                        status = '✓' if method == 'election-day' and diff > 0 else '⚠'
                        print(f'{status} {method:<20} {old_count:>10,} → {new_count:>10,} ({diff:+,})')
                    else:
                        print(f'  {method:<20} {new_count:>10,} (no change)')
                
                print(f'\n  {"TOTAL":<20} {last_total:>10,} → {current_total:>10,} ({current_total - last_total:+,})')
                
                # Verify the upload
                print('\n' + '=' * 80)
                if 'election-day' in current and current['election-day'] > baseline.get('election-day', 0):
                    new_ed = current['election-day'] - baseline.get('election-day', 0)
                    print(f'✓ SUCCESS! Added {new_ed:,} election-day records')
                    
                    if new_ed >= 23000 and new_ed <= 24000:
                        print(f'✓ Count looks correct! Expected ~23,029, got {new_ed:,}')
                    else:
                        print(f'⚠ Count unexpected. Expected ~23,029, got {new_ed:,}')
                    
                    # Show breakdown by party
                    rows2 = conn.execute('''
                        SELECT ve.party_voted, COUNT(*) as cnt
                        FROM voter_elections ve
                        JOIN voters v ON ve.vuid = v.vuid
                        WHERE ve.election_date = '2026-03-03'
                        AND v.county = 'Hidalgo'
                        AND ve.voting_method = 'election-day'
                        GROUP BY ve.party_voted
                    ''').fetchall()
                    
                    print('\nElection Day breakdown by party:')
                    for r in rows2:
                        print(f'  {r[0]:<15} {r[1]:>10,}')
                    
                elif 'early-voting' in current and current['early-voting'] > baseline.get('early-voting', 0):
                    new_ev = current['early-voting'] - baseline.get('early-voting', 0)
                    print(f'⚠ WARNING! Added {new_ev:,} early-voting records')
                    print('⚠ This suggests the upload form had "Early Voting" selected!')
                    print('⚠ The data should be tagged as "election-day" not "early-voting"')
                    print('\n⚠ ACTION NEEDED: Check the upload form dropdown!')
                
                else:
                    print('⚠ Unexpected change detected')
                
                print('=' * 80)
                
                # Update baseline
                baseline = current
                last_total = current_total
                
                # Stop monitoring after detecting change
                print('\nUpload detected. Stopping monitor.')
                break
            
            # Show progress indicator
            if check_count % 15 == 0:  # Every 30 seconds
                print(f'[{time.strftime("%H:%M:%S")}] Still monitoring... (checked {check_count} times)')

except KeyboardInterrupt:
    print('\n\nMonitoring stopped by user.')
    print('Final state:')
    
    with db.get_db() as conn:
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
