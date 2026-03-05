#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
r = conn.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN ve.is_new_voter=1 THEN 1 ELSE 0 END) as new,
        SUM(CASE WHEN v.birth_year IS NOT NULL AND v.birth_year > 0 THEN 1 ELSE 0 END) as has_age
    FROM voter_elections ve
    JOIN voters v ON ve.vuid=v.vuid
    WHERE ve.election_date='2026-03-03' AND v.county='Hidalgo'
""").fetchone()

print(f"Hidalgo County 2026 Primary:")
print(f"  Total: {r[0]:,}")
print(f"  New voters: {r[1]:,} ({r[1]/r[0]*100:.1f}%)")
print(f"  Have age data: {r[2]:,} ({r[2]/r[0]*100:.1f}%)")
print(f"  Missing age: {r[0]-r[2]:,} ({(r[0]-r[2])/r[0]*100:.1f}%)")

# Check prior election count
prior = conn.execute("""
    SELECT COUNT(DISTINCT ve.election_date)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid=v.vuid
    WHERE v.county='Hidalgo'
      AND ve.election_date < '2026-03-03'
      AND ve.party_voted IN ('Democratic', 'Republican')
""").fetchone()[0]

print(f"\nPrior elections in DB: {prior}")

conn.close()
