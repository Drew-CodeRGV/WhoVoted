#!/usr/bin/env python3
import sqlite3
import json

# Check database precincts
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
rows = conn.execute("""
    SELECT DISTINCT precinct, COUNT(*) as cnt 
    FROM voters 
    WHERE precinct IS NOT NULL AND precinct != ''
    GROUP BY precinct 
    ORDER BY cnt DESC 
    LIMIT 30
""").fetchall()

print("Top 30 precincts in database:")
for precinct, cnt in rows:
    print(f"  {precinct:20s} {cnt:6d} voters")

# Check boundary file precincts
print("\nPrecincts in boundary files:")
for fname in ['/opt/whovoted/public/data/precinct_boundaries.json',
              '/opt/whovoted/public/data/precinct_boundaries_cameron.json']:
    try:
        with open(fname) as f:
            data = json.load(f)
            precincts = []
            for feature in data.get('features', [])[:10]:
                props = feature.get('properties', {})
                pid = props.get('precinct_id') or props.get('precinct', '')
                precincts.append(pid)
            print(f"\n{fname}:")
            print(f"  Sample IDs: {precincts}")
    except:
        pass

conn.close()
