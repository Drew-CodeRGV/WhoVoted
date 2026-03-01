#!/usr/bin/env python3
"""Verify ABBM mail-in records in the DB."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row

# Check mail-in records
rows = conn.execute("""
    SELECT voting_method, party_voted, COUNT(*) as cnt
    FROM voter_elections
    WHERE voting_method = 'mail-in'
    GROUP BY voting_method, party_voted
""").fetchall()
print("Mail-in records:")
for r in rows:
    print(f"  {r['party_voted']}: {r['cnt']}")

# Check how many have geocoded coords
rows2 = conn.execute("""
    SELECT ve.party_voted, 
           COUNT(*) as total,
           SUM(CASE WHEN v.geocoded = 1 THEN 1 ELSE 0 END) as geocoded
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.voting_method = 'mail-in'
    GROUP BY ve.party_voted
""").fetchall()
print("\nGeocoded status:")
for r in rows2:
    print(f"  {r['party_voted']}: {r['geocoded']}/{r['total']} geocoded")

# Check overlap with early-voting records
overlap = conn.execute("""
    SELECT COUNT(DISTINCT mi.vuid) as cnt
    FROM voter_elections mi
    JOIN voter_elections ev ON mi.vuid = ev.vuid 
        AND ev.election_date = mi.election_date
        AND ev.voting_method = 'early-voting'
    WHERE mi.voting_method = 'mail-in'
      AND mi.election_date = '2026-03-03'
""").fetchone()
print(f"\nVoters who also have early-voting records: {overlap['cnt']}")

# Sample a few records
samples = conn.execute("""
    SELECT ve.vuid, ve.party_voted, ve.voting_method, v.firstname, v.lastname, v.address, v.geocoded
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.voting_method = 'mail-in'
    LIMIT 5
""").fetchall()
print("\nSample records:")
for s in samples:
    print(f"  VUID={s['vuid']}, {s['firstname']} {s['lastname']}, party={s['party_voted']}, "
          f"addr={'yes' if s['address'] else 'no'}, geocoded={s['geocoded']}")

conn.close()
