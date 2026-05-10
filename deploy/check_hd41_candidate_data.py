#!/usr/bin/env python3
"""Check what candidate-level data exists for HD-41."""
import sqlite3

DB = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB)

# Check all tables for anything candidate/result related
tables = [t[0] for t in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
print("All tables:", tables)

# Check if there's candidate-level data
for t in tables:
    if 'result' in t.lower() or 'candidate' in t.lower() or 'race' in t.lower():
        print(f"\nFound relevant table: {t}")
        cols = conn.execute(f"PRAGMA table_info({t})").fetchall()
        print(f"  Columns: {[c[1] for c in cols]}")
        cnt = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  Rows: {cnt}")

# Check voter_elections for March 3 in HD-41 — what fields do we have?
print("\n\nMarch 3 HD-41 voter_elections sample:")
sample = conn.execute("""
    SELECT ve.* FROM voter_elections ve
    INNER JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03' AND v.state_house_district = 'HD-41'
    LIMIT 5
""").fetchall()
cols = [d[0] for d in conn.execute("PRAGMA table_info(voter_elections)").fetchall()]
print(f"  Columns: {[c[1] for c in conn.execute('PRAGMA table_info(voter_elections)').fetchall()]}")
for row in sample:
    print(f"  {row}")

# Check if districts.json has HD-41 boundary
import json, os
dj = '/opt/whovoted/public/data/districts.json'
if os.path.exists(dj):
    d = json.load(open(dj))
    hd41 = [f for f in d['features'] if f.get('properties', {}).get('district_id') == 'HD-41']
    if hd41:
        geom = hd41[0]['geometry']
        print(f"\n\nHD-41 boundary in districts.json: type={geom['type']}, coords length={len(str(geom['coordinates']))}")
    else:
        print("\n\nHD-41 NOT in districts.json")

conn.close()
