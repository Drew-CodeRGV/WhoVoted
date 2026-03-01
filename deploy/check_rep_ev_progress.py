#!/usr/bin/env python3
"""Check REP EV processing progress."""
import sqlite3
import os
import glob

db_path = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(db_path)

# Check what tables exist
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print(f"Tables: {[t[0] for t in tables]}")

# Check for REP 2026 voters
try:
    count = conn.execute(
        "SELECT COUNT(*) FROM voters WHERE current_party=?",
        ("Republican",)
    ).fetchone()[0]
    print(f"Total Republican voters in DB: {count}")
except Exception as e:
    print(f"Error querying voters: {e}")

conn.close()

# Check for output GeoJSON files
data_dir = '/opt/whovoted/data'
rep_files = glob.glob(os.path.join(data_dir, '*2026*republican*'))
print(f"\nREP 2026 data files: {len(rep_files)}")
for f in sorted(rep_files):
    size = os.path.getsize(f)
    print(f"  {os.path.basename(f)} ({size:,} bytes)")

# Check public dir too
public_dir = '/opt/whovoted/public/data'
if os.path.exists(public_dir):
    rep_pub = glob.glob(os.path.join(public_dir, '*2026*republican*'))
    print(f"\nREP 2026 public files: {len(rep_pub)}")
    for f in sorted(rep_pub):
        size = os.path.getsize(f)
        print(f"  {os.path.basename(f)} ({size:,} bytes)")

# Check process status
import subprocess
result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
for line in result.stdout.split('\n'):
    if 'reprocess_rep' in line and 'grep' not in line:
        print(f"\nProcess: {line.strip()[:120]}")
