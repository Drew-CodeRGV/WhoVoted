import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("Tables:", tables)
if 'column_mappings' in tables:
    print("column_mappings table exists!")
    rows = conn.execute("SELECT * FROM column_mappings").fetchall()
    print(f"  Rows: {len(rows)}")
else:
    print("column_mappings table NOT found")
conn.close()
