#!/usr/bin/env python3
import sqlite3, json

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row

# Check the latest voter_elections for 2026 DEM
rows = conn.execute("""
    SELECT COUNT(*) as cnt, ve.voting_method 
    FROM voter_elections ve 
    WHERE ve.election_date = '2026-03-03' AND ve.party_voted = 'Democratic'
    GROUP BY ve.voting_method
""").fetchall()
print("=== 2026 DEM voter_elections by method ===")
for r in rows:
    print(f"  {r['voting_method']}: {r['cnt']}")

# Total 2026 DEM
total = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = '2026-03-03' AND party_voted = 'Democratic'").fetchone()[0]
print(f"  Total: {total}")

# Check how many of the 31904 are geocoded vs not
geocoded = conn.execute("""
    SELECT COUNT(*) FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03' AND ve.party_voted = 'Democratic' AND v.geocoded = 1
""").fetchone()[0]
not_geocoded = conn.execute("""
    SELECT COUNT(*) FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03' AND ve.party_voted = 'Democratic' AND (v.geocoded = 0 OR v.geocoded IS NULL)
""").fetchone()[0]
print(f"\n=== Geocoded status ===")
print(f"  Geocoded: {geocoded}")
print(f"  Not geocoded: {not_geocoded}")

# Sample some not-geocoded voters
rows = conn.execute("""
    SELECT v.vuid, v.firstname, v.lastname, v.address, v.city, v.geocoded, v.lat, v.lng
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03' AND ve.party_voted = 'Democratic' AND (v.geocoded = 0 OR v.geocoded IS NULL)
    LIMIT 15
""").fetchall()
print(f"\n=== Sample ungeocoded voters ===")
for r in rows:
    print(f"  {r['vuid']} {r['firstname']} {r['lastname']} | {r['address']} | geocoded={r['geocoded']} lat={r['lat']}")

# Check how many have "NOT AVAILABLE" address
na_count = conn.execute("""
    SELECT COUNT(*) FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03' AND ve.party_voted = 'Democratic' 
    AND v.address LIKE '%NOT AVAILABLE%'
""").fetchone()[0]
print(f"\n=== 'NOT AVAILABLE' addresses: {na_count} ===")

conn.close()
