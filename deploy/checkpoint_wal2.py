#!/usr/bin/env python3
"""Checkpoint the WAL file — exclusive mode for guaranteed success."""
import sqlite3, os, time
print("Opening DB in exclusive mode...")
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db', timeout=120)
conn.execute("PRAGMA locking_mode=EXCLUSIVE")
conn.execute("PRAGMA journal_mode=WAL")
print("Running TRUNCATE checkpoint...")
start = time.time()
result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
elapsed = time.time() - start
print(f"Checkpoint result: {result} ({elapsed:.1f}s)")
conn.execute("PRAGMA locking_mode=NORMAL")
conn.close()
print("Done. File sizes:")
for f in ['/opt/whovoted/data/whovoted.db', '/opt/whovoted/data/whovoted.db-wal', '/opt/whovoted/data/whovoted.db-shm']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  {os.path.basename(f)}: {size/1024/1024:.1f} MB")
