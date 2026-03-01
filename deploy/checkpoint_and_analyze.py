#!/usr/bin/env python3
"""Checkpoint WAL, analyze tables, check indexes."""
import sqlite3
import time

db_path = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(db_path, timeout=120)
conn.execute("PRAGMA journal_mode=WAL")

print("Checkpointing WAL...")
t0 = time.time()
r = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
print(f"  Result: {r} ({time.time()-t0:.1f}s)")

print("\nRunning ANALYZE...")
t0 = time.time()
conn.execute("ANALYZE")
print(f"  Done ({time.time()-t0:.1f}s)")

print("\nIndexes on voter_elections:")
rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='voter_elections'").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]}")

print("\nIndexes on voters:")
rows = conn.execute("SELECT name, sql FROM sqlite_master WHERE type='index' AND tbl_name='voters'").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]}")

print("\nTable sizes:")
for tbl in ['voters', 'voter_elections', 'election_summary']:
    try:
        r = conn.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
        print(f"  {tbl}: {r[0]:,}")
    except:
        print(f"  {tbl}: (not found)")

# Quick write benchmark
print("\nBenchmarking INSERT speed...")
conn.execute("CREATE TABLE IF NOT EXISTS _bench_test (id INTEGER PRIMARY KEY, val TEXT)")
conn.commit()

t0 = time.time()
params = [(i, f"test_{i}") for i in range(1000)]
conn.executemany("INSERT OR REPLACE INTO _bench_test VALUES (?, ?)", params)
conn.commit()
elapsed = time.time() - t0
print(f"  1000 simple inserts: {elapsed:.3f}s ({1000/elapsed:.0f} rows/s)")

conn.execute("DROP TABLE _bench_test")
conn.commit()

conn.close()
print("\nDone.")
