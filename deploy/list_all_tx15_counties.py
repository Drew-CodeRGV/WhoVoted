#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/whovoted.db')
c = conn.cursor()

c.execute("""
    SELECT v.county, COUNT(DISTINCT ve.vuid) as votes 
    FROM voter_elections ve 
    JOIN voters v ON ve.vuid = v.vuid 
    WHERE v.congressional_district = '15' 
    AND ve.election_date = '2026-03-03' 
    AND ve.party_voted = 'Democratic' 
    GROUP BY v.county 
    ORDER BY votes DESC
""")

print('All counties with TX-15 Dem votes:')
print('-' * 60)
total = 0
for r in c.fetchall():
    votes = r[1]
    total += votes
    print(f"  {r[0]:20s}: {votes:,} votes")

print('-' * 60)
print(f"  {'TOTAL':20s}: {total:,} votes")

conn.close()
