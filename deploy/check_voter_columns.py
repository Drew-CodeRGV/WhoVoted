#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('data/whovoted.db')
cursor = conn.cursor()
cursor.execute('PRAGMA table_info(voters)')
print('\nVoters table columns:')
for row in cursor.fetchall():
    print(f'  {row[1]} ({row[2]})')
conn.close()
