#!/usr/bin/env python3
"""
Analyze the upload pattern to identify which records are election day vs early voting.

The user says:
- 61,527 records are EARLY VOTING (uploaded earlier, marked as election-day by mistake)
- 23,029 records are ELECTION DAY (uploaded today: 16,857 + 6,172)

Let's see if we can identify them by looking at the pattern.
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    print('Analyzing Hidalgo County 2026 uploads by timestamp:')
    print('=' * 80)
    
    # Get all records grouped by second
    rows = conn.execute('''
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
        ORDER BY ve.created_at
    ''').fetchall()
    
    print(f'{"Timestamp":<20} {"Method":<15} {"Party":<15} {"Count":>10} {"Cumulative":>12}')
    print('=' * 80)
    
    cumulative = 0
    for r in rows:
        cumulative += r[3]
        print(f'{str(r[0]):<20} {r[1]:<15} {r[2]:<15} {r[3]:>10,} {cumulative:>12,}')
    
    # Try to identify patterns
    print('\n\nPATTERN ANALYSIS:')
    print('=' * 80)
    
    # If the user uploaded early voting first, then election day, we should see:
    # - First batch: ~61,527 records (early voting)
    # - Second batch: ~23,029 records (election day)
    
    # Let's check if there's a time gap
    rows2 = conn.execute('''
        SELECT 
            MIN(created_at) as first_upload,
            MAX(created_at) as last_upload,
            COUNT(DISTINCT created_at) as num_batches
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
    ''').fetchone()
    
    print(f'First upload: {rows2[0]}')
    print(f'Last upload: {rows2[1]}')
    print(f'Number of batches: {rows2[2]}')
    
    # Check if we can identify by looking at the last N records
    print('\n\nHYPOTHESIS: Last ~23,029 records are election day')
    print('=' * 80)
    
    # Get the timestamp where we cross the 23,029 threshold from the end
    rows3 = conn.execute('''
        WITH ranked AS (
            SELECT 
                ve.created_at,
                ve.voting_method,
                ve.party_voted,
                ve.vuid,
                ROW_NUMBER() OVER (ORDER BY ve.created_at DESC) as rn
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = '2026-03-03'
            AND v.county = 'Hidalgo'
            AND ve.voting_method = 'election-day'
        )
        SELECT 
            created_at,
            COUNT(*) as cnt
        FROM ranked
        WHERE rn <= 23029
        GROUP BY created_at
        ORDER BY created_at
    ''').fetchall()
    
    if rows3:
        print('Last 23,029 records span these timestamps:')
        for r in rows3:
            print(f'  {r[0]}: {r[1]:,} records')
        
        # Get the earliest timestamp from this set
        earliest_ed = rows3[0][0]
        print(f'\nIf we mark records from {earliest_ed} onwards as election-day,')
        print('and earlier records as early-voting, we get:')
        
        # Count how many that would be
        count_ed = conn.execute('''
            SELECT COUNT(*)
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = '2026-03-03'
            AND v.county = 'Hidalgo'
            AND ve.voting_method = 'election-day'
            AND ve.created_at >= ?
        ''', (earliest_ed,)).fetchone()[0]
        
        count_ev = conn.execute('''
            SELECT COUNT(*)
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = '2026-03-03'
            AND v.county = 'Hidalgo'
            AND ve.voting_method = 'election-day'
            AND ve.created_at < ?
        ''', (earliest_ed,)).fetchone()[0]
        
        print(f'  Early Voting (before {earliest_ed}): {count_ev:,}')
        print(f'  Election Day (from {earliest_ed} onwards): {count_ed:,}')
