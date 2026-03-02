#!/usr/bin/env python3
"""Verify statewide Texas numbers shown in the gazette."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("="*70)
print("STATEWIDE TEXAS 2026 PRIMARY VERIFICATION")
print("="*70)

# Total statewide votes
statewide = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as unique_voters,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
    FROM voter_elections ve
    WHERE ve.election_date = '2026-03-03'
      AND ve.party_voted IN ('Democratic', 'Republican')
""").fetchone()

print(f"\nStatewide Totals (from database):")
print(f"  Democratic: {statewide['dem']:,}")
print(f"  Republican: {statewide['rep']:,}")
print(f"  Total: {statewide['unique_voters']:,}")
print(f"  Dem %: {statewide['dem'] / statewide['unique_voters'] * 100:.1f}%")

print(f"\nGazette shows:")
print(f"  Total: 2,204,812")
print(f"  Democratic: 54.5%")
print(f"  Republican: 45.5%")

# New voters statewide
new_voters = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as new_total,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as new_dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as new_rep
    FROM voter_elections ve
    WHERE ve.election_date = '2026-03-03'
      AND ve.party_voted IN ('Democratic', 'Republican')
      AND NOT EXISTS (
          SELECT 1 FROM voter_elections ve2
          WHERE ve2.vuid = ve.vuid 
            AND ve2.election_date < '2026-03-03'
            AND ve2.party_voted != '' 
            AND ve2.party_voted IS NOT NULL
      )
""").fetchone()

print(f"\nNew Voters (first-time in any primary):")
print(f"  Democratic: {new_voters['new_dem']:,}")
print(f"  Republican: {new_voters['new_rep']:,}")
print(f"  Total: {new_voters['new_total']:,}")

# Party switchers
flips = conn.execute("""
    SELECT 
        ve_cur.party_voted as to_party,
        ve_prev.party_voted as from_party,
        COUNT(*) as cnt
    FROM voter_elections ve_cur
    JOIN voter_elections ve_prev ON ve_cur.vuid = ve_prev.vuid
    WHERE ve_cur.election_date = '2026-03-03'
      AND ve_prev.election_date = (
          SELECT MAX(ve2.election_date) 
          FROM voter_elections ve2
          WHERE ve2.vuid = ve_cur.vuid 
            AND ve2.election_date < '2026-03-03'
            AND ve2.party_voted != '' 
            AND ve2.party_voted IS NOT NULL
      )
      AND ve_cur.party_voted != ve_prev.party_voted
      AND ve_cur.party_voted IN ('Democratic', 'Republican')
      AND ve_prev.party_voted IN ('Democratic', 'Republican')
    GROUP BY ve_cur.party_voted, ve_prev.party_voted
""").fetchall()

r2d = sum(r['cnt'] for r in flips if r['from_party'] == 'Republican' and r['to_party'] == 'Democratic')
d2r = sum(r['cnt'] for r in flips if r['from_party'] == 'Democratic' and r['to_party'] == 'Republican')

print(f"\nParty Switchers:")
print(f"  R→D: {r2d:,}")
print(f"  D→R: {d2r:,}")
print(f"  Net: {r2d - d2r:+,} {'D' if r2d > d2r else 'R'}")

print(f"\nGazette shows:")
print(f"  R→D: 1,607")
print(f"  D→R: 1,587")
print(f"  Net: 20 D")

# 2024 comparison
comp_2024 = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as total_2024,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem_2024,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep_2024
    FROM voter_elections ve
    WHERE ve.election_date = '2024-03-05'
      AND ve.party_voted IN ('Democratic', 'Republican')
""").fetchone()

print(f"\n2024 Primary Totals:")
print(f"  Democratic: {comp_2024['dem_2024']:,}")
print(f"  Republican: {comp_2024['rep_2024']:,}")
print(f"  Total: {comp_2024['total_2024']:,}")

print(f"\nGazette shows:")
print(f"  2024 Dem: 28,504")
print(f"  2024 Rep: 27,174")

# County breakdown
print(f"\n" + "="*70)
print("TOP 10 COUNTIES BY TURNOUT")
print("="*70)

counties = conn.execute("""
    SELECT 
        v.county,
        COUNT(DISTINCT ve.vuid) as total,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND ve.party_voted IN ('Democratic', 'Republican')
      AND v.county IS NOT NULL
      AND v.county != ''
    GROUP BY v.county
    ORDER BY total DESC
    LIMIT 10
""").fetchall()

for row in counties:
    dem_pct = row['dem'] / row['total'] * 100 if row['total'] > 0 else 0
    print(f"  {row['county']:20s}: {row['total']:>8,} ({row['dem']:>7,} D {dem_pct:>5.1f}%, {row['rep']:>7,} R)")

conn.close()

print("\n" + "="*70)
print("CONCLUSION")
print("="*70)
print("""
The gazette is showing STATEWIDE Texas numbers, not Hidalgo County.
The header should say "Texas Statewide" not "Hidalgo County".

This needs to be fixed in the gazette/newspaper display logic.
""")
