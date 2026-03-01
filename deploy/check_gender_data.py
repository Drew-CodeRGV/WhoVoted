#!/usr/bin/env python3
"""Check if gender data exists in the voter GeoJSON and DB."""
import json
import sqlite3

# Check GeoJSON properties
with open('/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_democratic_cumulative_ev.json') as f:
    data = json.load(f)

print("=== GeoJSON Feature Properties (first voter) ===")
props = data['features'][0]['properties']
for k, v in sorted(props.items()):
    print(f"  {k}: {v}")

# Check if any property looks like gender
print("\n=== Checking for gender-like fields ===")
gender_fields = [k for k in props.keys() if any(g in k.lower() for g in ['gender', 'sex', 'male', 'female'])]
print(f"Gender-related fields: {gender_fields}")

# Check DB schema
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
print("\n=== DB Tables ===")
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    print(f"  {t[0]}")
    cols = conn.execute(f"PRAGMA table_info({t[0]})").fetchall()
    for c in cols:
        print(f"    {c[1]} ({c[2]})")

# Check voter_registry for gender
print("\n=== Checking voter_registry for gender ===")
try:
    sample = conn.execute("SELECT * FROM voter_registry LIMIT 1").fetchone()
    if sample:
        cols = [d[0] for d in conn.execute("PRAGMA table_info(voter_registry)").fetchall()]
        cols = [c[1] for c in conn.execute("PRAGMA table_info(voter_registry)").fetchall()]
        print(f"Columns: {cols}")
except Exception as e:
    print(f"No voter_registry table: {e}")

# Check voter_elections for gender
print("\n=== Checking voter_elections columns ===")
cols = conn.execute("PRAGMA table_info(voter_elections)").fetchall()
for c in cols:
    print(f"  {c[1]} ({c[2]})")

# Sample a few voters to see all data
print("\n=== Sample voter_elections rows ===")
rows = conn.execute("SELECT * FROM voter_elections LIMIT 3").fetchall()
col_names = [c[1] for c in cols]
for row in rows:
    print(dict(zip(col_names, row)))

conn.close()
