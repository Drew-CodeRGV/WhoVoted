#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    files = conn.execute('''
        SELECT DISTINCT source_file, COUNT(*) as cnt, MAX(created_at) as uploaded
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        GROUP BY source_file
        ORDER BY uploaded DESC
        LIMIT 5
    ''').fetchall()
    
    print('Recent 2026 files:')
    for f in files:
        print(f'{f[2]}: {f[0]} ({f[1]:,} voters)')
