#!/usr/bin/env python3
"""Check a sample voter's history to see what's being returned."""

import sqlite3
import sys

def main():
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    # First check the schema
    print('=== voter_elections table schema ===')
    schema = conn.execute("PRAGMA table_info(voter_elections)").fetchall()
    for col in schema:
        print(f"{col['name']}: {col['type']}")
    print()
    
    # Get a voter from 2026 election
    print('=== Sample voter from 2026 election ===')
    voter = conn.execute('''
        SELECT vuid
        FROM voter_elections 
        WHERE election_date = '2026-03-03'
        LIMIT 1
    ''').fetchone()
    
    if not voter:
        print('No voters found')
        return
    
    vuid = voter['vuid']
    print(f'VUID: {vuid}')
    print()
    
    # Get full history for this voter
    print('=== Full voting history ===')
    history = conn.execute('''
        SELECT *
        FROM voter_elections 
        WHERE vuid = ?
        ORDER BY election_date
    ''', (vuid,)).fetchall()
    
    for h in history:
        method_label = 'EV' if 'early' in h['voting_method'].lower() else 'ED'
        print(f"{h['election_year']} {method_label} ({h['voting_method']}): {h['party_voted']} - {h['election_type']}")
    
    print(f'\nTotal elections: {len(history)}')
    
    conn.close()

if __name__ == '__main__':
    main()
