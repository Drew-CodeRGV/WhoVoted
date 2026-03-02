#!/usr/bin/env python3
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
c = conn.cursor()

# Check overall geocoding coverage
r = c.execute('''
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN lat IS NOT NULL AND lng IS NOT NULL THEN 1 ELSE 0 END) as geocoded,
        SUM(CASE WHEN lat IS NULL OR lng IS NULL THEN 1 ELSE 0 END) as not_geocoded
    FROM voters
''').fetchone()

print(f"Total voters: {r[0]:,}")
print(f"Geocoded: {r[1]:,} ({r[1]*100.0/r[0]:.2f}%)")
print(f"Not geocoded: {r[2]:,} ({r[2]*100.0/r[0]:.2f}%)")

# Check 2026 primary voters specifically
r2 = c.execute('''
    SELECT 
        COUNT(DISTINCT ve.vuid) as total,
        SUM(CASE WHEN v.lat IS NOT NULL AND v.lng IS NOT NULL THEN 1 ELSE 0 END) as geocoded
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
''').fetchone()

print(f"\n2026 Primary voters:")
print(f"Total: {r2[0]:,}")
print(f"Geocoded: {r2[1]:,} ({r2[1]*100.0/r2[0]:.2f}%)")
print(f"Not geocoded: {r2[0]-r2[1]:,} ({(r2[0]-r2[1])*100.0/r2[0]:.2f}%)")

conn.close()
