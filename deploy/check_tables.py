#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
tables = [row[0] for row in conn.execute('SELECT name FROM sqlite_master WHERE type="table"').fetchall()]
print("All tables:", tables)
print("\nTables with 'cache' or 'district':", [t for t in tables if 'cache' in t.lower() or 'district' in t.lower()])
