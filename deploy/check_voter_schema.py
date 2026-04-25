import sqlite3
c = sqlite3.connect('/opt/whovoted/data/whovoted.db')
cols = [r[1] for r in c.execute("PRAGMA table_info(voters)").fetchall()]
print("voters columns:", cols)
# Sample a row
r = c.execute("SELECT * FROM voters LIMIT 1").fetchone()
for i, col in enumerate(cols):
    print(f"  {col}: {r[i]}")
c.close()
