#!/usr/bin/env python3
"""Check why voters are unmatched in 2026 early vote."""
import sys, os
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')
import database as db
db.init_db()
conn = db.get_connection()

# Count 2026 voters by geocoded status
total = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-23'
""").fetchone()[0]

geocoded = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-23' AND v.geocoded = 1
""").fetchone()[0]

no_coords = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-23' AND (v.geocoded = 0 OR v.geocoded IS NULL)
""").fetchone()[0]

has_addr_no_coords = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-23'
      AND (v.geocoded = 0 OR v.geocoded IS NULL)
      AND v.address IS NOT NULL AND v.address != ''
""").fetchone()[0]

no_addr = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-23'
      AND (v.address IS NULL OR v.address = '')
""").fetchone()[0]

# VUIDs in voter_elections but NOT in voters table at all
not_in_voters = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    LEFT JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-23' AND v.vuid IS NULL
""").fetchone()[0]

print(f"2026 election voters: {total}")
print(f"  Geocoded: {geocoded}")
print(f"  No coords: {no_coords}")
print(f"    Has address but no coords: {has_addr_no_coords}")
print(f"    No address at all: {no_addr}")
print(f"  Not in voters table: {not_in_voters}")

# Sample some unmatched
print("\nSample unmatched voters (no address):")
samples = conn.execute("""
    SELECT ve.vuid, v.address, v.city, v.geocoded, v.firstname, v.lastname
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-23'
      AND (v.address IS NULL OR v.address = '')
    LIMIT 10
""").fetchall()
for s in samples:
    print(f"  VUID: {s[0]}, addr: '{s[1]}', city: '{s[2]}', geocoded: {s[3]}, name: {s[4]} {s[5]}")

# Check the 2026-02-24 date too (the new uploads used today's date)
total_24 = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    WHERE ve.election_date = '2026-02-24'
""").fetchone()[0]
print(f"\n2026-02-24 election voters: {total_24}")

if total_24 > 0:
    geocoded_24 = conn.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-02-24' AND v.geocoded = 1
    """).fetchone()[0]
    no_coords_24 = conn.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-02-24' AND (v.geocoded = 0 OR v.geocoded IS NULL)
    """).fetchone()[0]
    has_addr_24 = conn.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-02-24'
          AND (v.geocoded = 0 OR v.geocoded IS NULL)
          AND v.address IS NOT NULL AND v.address != ''
    """).fetchone()[0]
    no_addr_24 = conn.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-02-24'
          AND (v.address IS NULL OR v.address = '')
    """).fetchone()[0]
    print(f"  Geocoded: {geocoded_24}")
    print(f"  No coords: {no_coords_24}")
    print(f"    Has address but no coords: {has_addr_24}")
    print(f"    No address at all: {no_addr_24}")
