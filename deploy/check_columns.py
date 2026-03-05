#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

conn = db.get_connection()
cols = [r[1] for r in conn.execute("PRAGMA table_info(voters)").fetchall()]
print("Voters table columns:", cols)
