#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('data/whovoted.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM voters WHERE congressional_district = '15'")
total = c.fetchone()[0]
print(f'Total voters in TX-15: {total:,}')

c.execute("""
    SELECT COUNT(DISTINCT ve.vuid) 
    FROM voter_elections ve 
    JOIN voters v ON ve.vuid = v.vuid 
    WHERE v.congressional_district = '15' 
    AND ve.election_date = '2026-03-03' 
    AND ve.party_voted IN ('Democratic', 'Republican')
""")
voted = c.fetchone()[0]
print(f'Voters who voted in 2026-03-03 primary: {voted:,}')

c.execute("""
    SELECT COUNT(DISTINCT ve.vuid) 
    FROM voter_elections ve 
    JOIN voters v ON ve.vuid = v.vuid 
    WHERE v.congressional_district = '15' 
    AND ve.election_date = '2024-03-05' 
    AND ve.party_voted IN ('Democratic', 'Republican')
""")
voted_2024 = c.fetchone()[0]
print(f'Voters who voted in 2024-03-05 primary: {voted_2024:,}')

conn.close()
