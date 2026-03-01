#!/usr/bin/env python3
import sqlite3
c = sqlite3.connect('/opt/whovoted/data/whovoted.db')
r = c.execute("""
    SELECT COUNT(*),
           SUM(CASE WHEN geocoded=1 THEN 1 ELSE 0 END),
           SUM(CASE WHEN geocoded=0 OR geocoded IS NULL THEN 1 ELSE 0 END)
    FROM voters WHERE county='Hidalgo'
""").fetchone()
print(f"Total voters: {r[0]:,}")
print(f"Geocoded:     {r[1]:,}")
print(f"Not geocoded: {r[2]:,}")
print(f"Coverage:     {r[1]/r[0]*100:.1f}%")
