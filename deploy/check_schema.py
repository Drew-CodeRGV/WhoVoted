#!/usr/bin/env python3
"""Check database schema."""

import sqlite3

def main():
    conn = sqlite3.connect('data/whovoted.db')
    conn.row_factory = sqlite3.Row
    
    print('=== election_summary table schema ===')
    schema = conn.execute("PRAGMA table_info(election_summary)").fetchall()
    for col in schema:
        print(f"{col['name']}: {col['type']}")
    
    print('\n=== voters table schema ===')
    schema = conn.execute("PRAGMA table_info(voters)").fetchall()
    for col in schema:
        print(f"{col['name']}: {col['type']}")
    
    conn.close()

if __name__ == '__main__':
    main()
