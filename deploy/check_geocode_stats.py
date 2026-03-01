#!/usr/bin/env python3
"""Check current geocoding stats for the voter DB."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

db.init_db()
conn = db.get_connection()

total = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo'").fetchone()[0]
geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo' AND geocoded=1").fetchone()[0]
failed = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo' AND geocoded=-1").fetchone()[0]
ungeocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE county='Hidalgo' AND geocoded=0").fetchone()[0]

voted = conn.execute("SELECT COUNT(DISTINCT v.vuid) FROM voters v INNER JOIN voter_elections ve ON v.vuid=ve.vuid WHERE v.county='Hidalgo'").fetchone()[0]
voted_geo = conn.execute("SELECT COUNT(DISTINCT v.vuid) FROM voters v INNER JOIN voter_elections ve ON v.vuid=ve.vuid WHERE v.county='Hidalgo' AND v.geocoded=1").fetchone()[0]
voted_ungeo = conn.execute("SELECT COUNT(DISTINCT v.vuid) FROM voters v INNER JOIN voter_elections ve ON v.vuid=ve.vuid WHERE v.county='Hidalgo' AND v.geocoded=0").fetchone()[0]

cache = conn.execute("SELECT COUNT(*) FROM geocoding_cache").fetchone()[0]
elections = conn.execute("SELECT COUNT(*) FROM voter_elections").fetchone()[0]

print(f"=== Hidalgo County Voter DB ===")
print(f"Total voters:      {total:,}")
print(f"Geocoded:          {geocoded:,} ({geocoded/total*100:.1f}%)")
print(f"Failed geocode:    {failed:,}")
print(f"Need geocoding:    {ungeocoded:,}")
print()
print(f"=== Voters Who Voted ===")
print(f"Total voted:       {voted:,}")
print(f"Voted + geocoded:  {voted_geo:,} ({voted_geo/voted*100:.1f}%)")
print(f"Voted + ungeo:     {voted_ungeo:,}")
print()
print(f"=== Other Stats ===")
print(f"Geocoding cache:   {cache:,} addresses")
print(f"Election records:  {elections:,}")
