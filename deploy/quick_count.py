#!/usr/bin/env python3
import sqlite3, time
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db', timeout=300)
start = time.time()
voters = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
t1 = time.time() - start
print(f"voters: {voters:,} ({t1:.1f}s)")
start = time.time()
ve = conn.execute("SELECT COUNT(*) FROM voter_elections").fetchone()[0]
t2 = time.time() - start
print(f"voter_elections: {ve:,} ({t2:.1f}s)")
conn.close()
