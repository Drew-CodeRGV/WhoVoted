#!/usr/bin/env python3
import sqlite3, sys
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row
rows = conn.execute("""
    SELECT v.vuid, v.firstname, v.lastname, v.address, v.city, v.zip, v.lat, v.lng, v.geocoded,
           ve.election_date, ve.voting_method
    FROM voters v
    LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = '2026-05-10'
    WHERE v.lastname LIKE '%PATEL%' AND v.firstname LIKE '%PRIYANKA%'
""").fetchall()
for r in rows:
    print(dict(r))
if not rows:
    print("NOT FOUND in voters table")
conn.close()
