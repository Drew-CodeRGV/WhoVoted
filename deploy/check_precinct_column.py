#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cols = [row[1] for row in conn.execute('PRAGMA table_info(voters)').fetchall()]
precinct_cols = [c for c in cols if 'precinct' in c.lower()]
print("Precinct columns:", precinct_cols)
print("\nAll columns:", cols)
