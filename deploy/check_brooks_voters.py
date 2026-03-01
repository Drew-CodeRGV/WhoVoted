#!/usr/bin/env python3
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

r = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Brooks'").fetchone()
print(f"Brooks voters in voters table: {r[0]}")

r = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE source_file LIKE '%Voting_History%'").fetchone()
print(f"Brooks VUIDs in voter_elections: {r[0]}")

r = conn.execute("SELECT COUNT(*) FROM voters v JOIN voter_elections ve ON v.vuid=ve.vuid WHERE ve.source_file LIKE '%Voting_History%'").fetchone()
print(f"Brooks VUIDs that exist in voters table: {r[0]}")

# Check what county the Brooks VUIDs have in voters table
r = conn.execute("""
    SELECT v.county, COUNT(*) FROM voters v 
    JOIN voter_elections ve ON v.vuid=ve.vuid 
    WHERE ve.source_file LIKE '%Voting_History%'
    GROUP BY v.county
""").fetchall()
print(f"County distribution of Brooks VUIDs in voters: {r}")

# Check the voters table schema for county
r = conn.execute("SELECT DISTINCT county FROM voters WHERE county IS NOT NULL AND county != '' LIMIT 20").fetchall()
print(f"Distinct counties in voters table: {[x[0] for x in r]}")
