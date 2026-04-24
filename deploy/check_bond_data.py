#!/usr/bin/env python3
import sqlite3, json, os
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
ZIPS = ('78501','78502','78503','78504','78505')
ph = ','.join('?' * len(ZIPS))

total = conn.execute(f"SELECT COUNT(*) FROM voters WHERE zip IN ({ph}) AND lat IS NOT NULL", ZIPS).fetchone()[0]
print(f"Registered voters in McAllen (geocoded): {total}")

voted = conn.execute(f"""SELECT COUNT(DISTINCT v.vuid) FROM voters v 
    JOIN voter_elections ve ON v.vuid=ve.vuid 
    WHERE ve.election_date='2026-05-10' AND v.zip IN ({ph}) AND v.lat IS NOT NULL""", ZIPS).fetchone()[0]
print(f"Voted in bond: {voted}")
print(f"Registered NOT voted: {total - voted}")

cols = [r[1] for r in conn.execute('PRAGMA table_info(voters)').fetchall()]
dist_cols = [c for c in cols if 'district' in c.lower() or 'commission' in c.lower()]
print(f"District columns: {dist_cols}")

if 'commissioner_district' in cols:
    rows = conn.execute(f"SELECT commissioner_district, COUNT(*) FROM voters WHERE zip IN ({ph}) AND commissioner_district IS NOT NULL GROUP BY commissioner_district", ZIPS).fetchall()
    print("Commissioner districts in McAllen:")
    for r in rows:
        print(f"  {r[0]}: {r[1]} voters")

# Check districts.json
dpath = '/opt/whovoted/public/data/districts.json'
if os.path.exists(dpath):
    with open(dpath) as f:
        data = json.load(f)
    types = set()
    for feat in data.get('features', []):
        types.add(feat.get('properties', {}).get('district_type', ''))
    print(f"District types in districts.json: {types}")

# Check precinct distribution for McAllen
rows = conn.execute(f"SELECT precinct, COUNT(*) as cnt FROM voters WHERE zip IN ({ph}) AND precinct IS NOT NULL GROUP BY precinct ORDER BY cnt DESC LIMIT 20", ZIPS).fetchall()
print(f"\nTop 20 precincts in McAllen:")
for r in rows:
    print(f"  Pct {r[0]}: {r[1]} voters")

conn.close()
