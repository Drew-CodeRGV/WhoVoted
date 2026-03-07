#!/usr/bin/env python3
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Checking voter_elections table for precinct data:")
cursor.execute("""
    SELECT COUNT(*), COUNT(precinct) 
    FROM voter_elections 
    WHERE election_date = '2026-03-03'
""")
total, with_precinct = cursor.fetchone()
print(f"  Total voting records: {total:,}")
print(f"  Records with precinct: {with_precinct:,}")
print(f"  Percentage: {100 * with_precinct / total:.1f}%")

print("\nSample precincts from voting records:")
cursor.execute("""
    SELECT DISTINCT precinct 
    FROM voter_elections 
    WHERE election_date = '2026-03-03' 
    AND precinct IS NOT NULL 
    AND precinct != ''
    LIMIT 20
""")
for (precinct,) in cursor.fetchall():
    print(f"  '{precinct}'")

print("\nD15 voters - comparing voter table precinct vs voting record precinct:")
cursor.execute("""
    SELECT 
        v.precinct as voter_precinct,
        ve.precinct as voting_precinct,
        COUNT(*) as count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
    AND ve.election_date = '2026-03-03'
    AND ve.party_voted = 'Democratic'
    GROUP BY v.precinct, ve.precinct
    LIMIT 10
""")
print("\n  Voter Precinct | Voting Precinct | Count")
for voter_prec, voting_prec, count in cursor.fetchall():
    print(f"  {str(voter_prec):<14} | {str(voting_prec):<15} | {count}")

conn.close()
