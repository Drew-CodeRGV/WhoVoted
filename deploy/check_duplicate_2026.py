#!/usr/bin/env python3
"""Check for voters with duplicate 2026 election entries."""

import sqlite3
import sys

def main():
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    print('=== Voters with multiple 2026 entries ===')
    dupes = conn.execute('''
        SELECT vuid, COUNT(*) as cnt, GROUP_CONCAT(voting_method) as methods
        FROM voter_elections 
        WHERE election_date = '2026-03-03'
        GROUP BY vuid 
        HAVING COUNT(*) > 1
        LIMIT 10
    ''').fetchall()
    
    for d in dupes:
        print(f'VUID: {d["vuid"]}, Count: {d["cnt"]}, Methods: {d["methods"]}')
        
        # Get details for this voter
        details = conn.execute('''
            SELECT vuid, election_date, voting_method, party_voted, county
            FROM voter_elections 
            WHERE vuid = ? AND election_date = '2026-03-03'
        ''', (d['vuid'],)).fetchall()
        
        for detail in details:
            print(f'  - {detail["voting_method"]}: {detail["party_voted"]} in {detail["county"]}')
        print()
    
    # Count total duplicates
    total = conn.execute('''
        SELECT COUNT(DISTINCT vuid) 
        FROM (
            SELECT vuid 
            FROM voter_elections 
            WHERE election_date = '2026-03-03'
            GROUP BY vuid 
            HAVING COUNT(*) > 1
        )
    ''').fetchone()[0]
    
    print(f'Total voters with duplicate 2026 entries: {total}')
    
    # Check if it's the same voting method or different
    same_method = conn.execute('''
        SELECT COUNT(DISTINCT vuid)
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        GROUP BY vuid, voting_method
        HAVING COUNT(*) > 1
    ''').fetchone()
    
    if same_method:
        print(f'Voters with duplicate entries for SAME voting method: {same_method[0]}')
    
    conn.close()

if __name__ == '__main__':
    main()
