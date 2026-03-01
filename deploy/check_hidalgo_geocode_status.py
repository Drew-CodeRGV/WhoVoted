#!/usr/bin/env python3
"""Check geocoding status of Hidalgo County voters."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
c = conn.cursor()

# Overall counts
c.execute("""
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN geocoded=1 THEN 1 ELSE 0 END) as geocoded,
        SUM(CASE WHEN (geocoded=0 OR geocoded IS NULL) AND address IS NOT NULL AND address != '' THEN 1 ELSE 0 END) as ungeocoded_with_addr,
        SUM(CASE WHEN (geocoded=0 OR geocoded IS NULL) AND (address IS NULL OR address = '') THEN 1 ELSE 0 END) as ungeocoded_no_addr
    FROM voters WHERE county='Hidalgo'
""")
row = c.fetchone()
print(f"Hidalgo County voters:")
print(f"  Total: {row[0]:,}")
print(f"  Geocoded: {row[1]:,}")
print(f"  Ungeocoded (has address): {row[2]:,}")
print(f"  Ungeocoded (no address): {row[3]:,}")

# How many have voted in 2026?
c.execute("""
    SELECT COUNT(DISTINCT ve.vuid) 
    FROM voter_elections ve 
    JOIN voters v ON ve.vuid = v.vuid 
    WHERE v.county='Hidalgo' AND ve.election_date='2026-03-03'
""")
voted_2026 = c.fetchone()[0]
print(f"\n  Voted in 2026 primary: {voted_2026:,}")
print(f"  Registered but NOT voted: {row[0] - voted_2026:,}")

# Sample ungeocoded addresses
c.execute("""
    SELECT address, city, zip FROM voters 
    WHERE county='Hidalgo' AND (geocoded=0 OR geocoded IS NULL) AND address IS NOT NULL AND address != ''
    LIMIT 5
""")
print(f"\nSample ungeocoded addresses:")
for r in c.fetchall():
    print(f"  {r[0]}, {r[1]}, {r[2]}")

conn.close()
