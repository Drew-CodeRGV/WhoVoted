#!/usr/bin/env python3
"""Check a sample voter's history to see what's being returned."""

import sqlite3
import sys

def main():
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    # Get a voter from Hidalgo County who voted in 2026
    print('=== Sample voter from 2026 election ===')
    voter = conn.execute('''
        SELECT vuid, county
        FROM voter_elections 
        WHERE election_date = '2026-03-03' AND county = 'Hidalgo'
        LIMIT 1
    ''').fetchone()
    
    if not voter:
        print('No voters found')
        return
    
    vuid = voter['vuid']
    print(f'VUID: {vuid}')
    print(f'County: {voter["county"]}')
    print()
    
    # Get full history for this voter
    print('=== Full voting history ===')
    history = conn.execute('''
        SELECT election_date, election_year, election_type, voting_method, party_voted, county
        FROM voter_elections 
        WHERE vuid = ?
        ORDER BY election_date
    ''', (vuid,)).fetchall()
    
    for h in history:
        method_label = 'EV' if 'early' in h['voting_method'].lower() else 'ED'
        print(f"{h['election_year']} {method_label} ({h['voting_method']}): {h['party_voted']} - {h['election_type']} in {h['county']}")
    
    print(f'\nTotal elections: {len(history)}')
    
    conn.close()

if __name__ == '__main__':
    main()
