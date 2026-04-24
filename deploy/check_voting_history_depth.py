#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
ZIPS = ('78501','78502','78503','78504','78505')
ph = ','.join('?' * len(ZIPS))

# How many elections do we have per voter?
rows = conn.execute(f"""
    SELECT ve_count, COUNT(*) as voters FROM (
        SELECT v.vuid, COUNT(ve.vuid) as ve_count
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
        GROUP BY v.vuid
    ) GROUP BY ve_count ORDER BY ve_count
""", ZIPS).fetchall()
print("Voting history distribution (McAllen):")
for r in rows:
    print(f"  {r[0]} elections: {r[1]} voters")

# What election dates exist?
dates = conn.execute("SELECT DISTINCT election_date, COUNT(*) FROM voter_elections GROUP BY election_date ORDER BY election_date DESC LIMIT 10").fetchall()
print("\nRecent election dates:")
for d in dates:
    print(f"  {d[0]}: {d[1]} records")

# Sample: a voter with multiple elections
sample = conn.execute(f"""
    SELECT v.vuid, v.firstname, v.lastname, COUNT(ve.vuid) as elections
    FROM voters v JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.zip IN ({ph})
    GROUP BY v.vuid HAVING elections > 2
    LIMIT 3
""", ZIPS).fetchall()
print("\nSample multi-election voters:")
for s in sample:
    print(f"  {s[1]} {s[2]} (VUID {s[0]}): {s[3]} elections")
    hist = conn.execute("SELECT election_date, voting_method FROM voter_elections WHERE vuid = ? ORDER BY election_date", (s[0],)).fetchall()
    for h in hist:
        print(f"    {h[0]} ({h[1]})")

conn.close()
