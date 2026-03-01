#!/usr/bin/env python3
"""Checkpoint the WAL file to reclaim space and speed up operations."""
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db', timeout=60)
conn.execute("PRAGMA journal_mode=WAL")
result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
print(f"WAL checkpoint result: {result}")
# result = (busy, log_pages, checkpointed_pages)
conn.close()
import os
for f in ['/opt/whovoted/data/whovoted.db', '/opt/whovoted/data/whovoted.db-wal', '/opt/whovoted/data/whovoted.db-shm']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  {f}: {size/1024/1024:.1f} MB")
