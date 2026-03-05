#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
rows = conn.execute("""
    SELECT DISTINCT district_id, district_name 
    FROM district_cache 
    WHERE district_id LIKE 'TX-15%'
""").fetchall()

for r in rows:
    print(f"{r[0]}: {r[1]}")
    safe_name = r[1].replace(' ', '_').replace('/', '_')
    print(f"  Cache filename: district_report_{safe_name}.json")

conn.close()
