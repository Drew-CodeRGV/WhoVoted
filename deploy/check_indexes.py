#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
print("=== INDEXES ===")
for r in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' ORDER BY name").fetchall():
    print(f"{r[0]}: {r[1]}")
print("\n=== TABLE SCHEMAS ===")
for r in conn.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND name IN ('voters','voter_elections') ORDER BY name").fetchall():
    print(f"\n{r[0]}:\n{r[1]}")
print("\n=== ROW COUNTS ===")
print("voters:", conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0])
print("voter_elections:", conn.execute("SELECT COUNT(*) FROM voter_elections").fetchone()[0])
