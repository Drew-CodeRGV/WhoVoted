#!/usr/bin/env python3
import sqlite3

DB = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB)

print("=== 2024 Flips (party switched from previous election) ===")
rows = conn.execute("""
    SELECT ve_current.party_voted as to_p, ve_prev.party_voted as from_p, COUNT(*) as cnt
    FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    WHERE ve_current.election_date = '2024-03-05'
      AND ve_prev.election_date = (
          SELECT MAX(ve2.election_date) FROM voter_elections ve2
          WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
            AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
      AND ve_current.party_voted != ve_prev.party_voted
      AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
    GROUP BY ve_current.party_voted, ve_prev.party_voted
""").fetchall()
for r in rows:
    print(f"  {r[1]} -> {r[0]}: {r[2]}")

print("\n=== Previous election dates for 2024 flippers ===")
rows2 = conn.execute("""
    SELECT ve_prev.election_date, COUNT(*)
    FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    WHERE ve_current.election_date = '2024-03-05'
      AND ve_prev.election_date = (
          SELECT MAX(ve2.election_date) FROM voter_elections ve2
          WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
            AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
      AND ve_current.party_voted != ve_prev.party_voted
      AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
    GROUP BY ve_prev.election_date ORDER BY ve_prev.election_date
""").fetchall()
for r in rows2:
    print(f"  {r[0]}: {r[1]} flippers")

print("\n=== Total voters by party per election ===")
for edate in ['2016-03-01', '2022-03-01', '2024-03-05', '2026-03-03']:
    rows3 = conn.execute("SELECT party_voted, COUNT(*) FROM voter_elections WHERE election_date=? AND party_voted != '' GROUP BY party_voted", (edate,)).fetchall()
    total = sum(r[1] for r in rows3)
    parts = ', '.join(f"{r[0]}={r[1]}" for r in rows3)
    print(f"  {edate}: total={total} ({parts})")

print("\n=== Overlap: 2024 voters who also voted in 2022 ===")
overlap = conn.execute("""
    SELECT COUNT(DISTINCT ve24.vuid) FROM voter_elections ve24
    JOIN voter_elections ve22 ON ve24.vuid = ve22.vuid
    WHERE ve24.election_date='2024-03-05' AND ve22.election_date='2022-03-01'
""").fetchone()[0]
print(f"  {overlap} voters voted in both 2022 and 2024")

# Sanity: check if 2016 data exists and could be the "previous" for some 2024 voters
print("\n=== 2024 voters whose ONLY previous election was 2016 ===")
only_2016 = conn.execute("""
    SELECT COUNT(*) FROM voter_elections ve24
    WHERE ve24.election_date = '2024-03-05'
      AND EXISTS (SELECT 1 FROM voter_elections ve16 WHERE ve16.vuid = ve24.vuid AND ve16.election_date = '2016-03-01')
      AND NOT EXISTS (SELECT 1 FROM voter_elections ve22 WHERE ve22.vuid = ve24.vuid AND ve22.election_date = '2022-03-01')
""").fetchone()[0]
print(f"  {only_2016} voters (skipped 2022, came back in 2024)")

conn.close()
