#!/usr/bin/env python3
"""
Check ALL recent uploads to find the election day data
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    print('All uploads for Hidalgo County 2026 Primary:')
    print('=' * 80)
    
    # Get all voter_elections records for Hidalgo County 2026
    rows = conn.execute('''
        SELECT 
            ve.created_at,
            ve.source_file,
            ve.voting_method,
            ve.party_voted,
            COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        GROUP BY ve.created_at, ve.source_file, ve.voting_method, ve.party_voted
        ORDER BY ve.created_at DESC
        LIMIT 50
    ''').fetchall()
    
    if not rows:
        print('No uploads found')
    else:
        print(f'{"Timestamp":<20} {"File":<40} {"Method":<15} {"Party":<15} {"Count":>10}')
        print('=' * 80)
        for r in rows:
            print(f'{str(r[0]):<20} {(r[1] or "NULL"):<40} {r[2]:<15} {r[3]:<15} {r[4]:>10,}')
    
    # Summary by voting method
    print('\n\nSummary by voting method:')
    print('=' * 60)
    rows2 = conn.execute('''
        SELECT 
            ve.voting_method,
            ve.party_voted,
            COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        GROUP BY ve.voting_method, ve.party_voted
        ORDER BY ve.voting_method, ve.party_voted
    ''').fetchall()
    
    for r in rows2:
        print(f'{r[0]:<20} {r[1]:<15} {r[2]:>10,}')
    
    # Check if there are any records with source_file NOT NULL
    print('\n\nRecords with source_file NOT NULL:')
    print('=' * 60)
    rows3 = conn.execute('''
        SELECT 
            ve.source_file,
            ve.voting_method,
            COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        AND v.county = 'Hidalgo'
        AND ve.source_file IS NOT NULL
        GROUP BY ve.source_file, ve.voting_method
    ''').fetchall()
    
    if rows3:
        for r in rows3:
            print(f'{r[0]:<60} {r[1]:<15} {r[2]:>10,}')
    else:
        print('All records have source_file = NULL')
