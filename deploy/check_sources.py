#!/usr/bin/env python3
"""Check existing data sources in voter_elections table."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

print("=== Distinct source_file patterns ===")
rows = conn.execute("""
    SELECT DISTINCT source_file, COUNT(*) as cnt 
    FROM voter_elections 
    GROUP BY source_file 
    ORDER BY cnt DESC
""").fetchall()
for sf, cnt in rows:
    print(f"  {cnt:>8,}  {sf}")

print("\n=== Distinct source values in voters table ===")
rows = conn.execute("""
    SELECT DISTINCT source, COUNT(*) as cnt 
    FROM voters 
    GROUP BY source 
    ORDER BY cnt DESC
""").fetchall()
for src, cnt in rows:
    print(f"  {cnt:>8,}  {src}")

print("\n=== Hidalgo 2026 early-voting counts by source_file ===")
rows = conn.execute("""
    SELECT ve.source_file, COUNT(*) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' 
      AND ve.election_date = '2026-03-03'
      AND ve.voting_method = 'early-voting'
    GROUP BY ve.source_file
    ORDER BY cnt DESC
""").fetchall()
for sf, cnt in rows:
    print(f"  {cnt:>8,}  {sf}")

print("\n=== Column info for voter_elections ===")
for row in conn.execute("PRAGMA table_info(voter_elections)").fetchall():
    print(f"  {row}")

conn.close()
