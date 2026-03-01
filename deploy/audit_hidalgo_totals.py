#!/usr/bin/env python3
"""Audit Hidalgo County 2026 primary totals against expected numbers."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Expected totals (from user)
EXPECTED_DEM = 49664
EXPECTED_REP = 13217
EXPECTED_TOTAL = 62881

print("=" * 70)
print("HIDALGO COUNTY 2026 PRIMARY AUDIT")
print("=" * 70)

# 1. Total unique voters by party across ALL voting methods
print("\n--- All voting methods combined (unique voters) ---")
row = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as total,
        COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
        COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
""").fetchone()
db_total = row['total']
db_dem = row['dem']
db_rep = row['rep']
print(f"  DB Total:  {db_total:>6,}   (expected {EXPECTED_TOTAL:>6,}, diff {db_total - EXPECTED_TOTAL:+,})")
print(f"  DB DEM:    {db_dem:>6,}   (expected {EXPECTED_DEM:>6,}, diff {db_dem - EXPECTED_DEM:+,})")
print(f"  DB REP:    {db_rep:>6,}   (expected {EXPECTED_REP:>6,}, diff {db_rep - EXPECTED_REP:+,})")

# 2. Breakdown by voting method
print("\n--- By voting method ---")
rows = conn.execute("""
    SELECT 
        ve.voting_method,
        ve.party_voted,
        COUNT(DISTINCT ve.vuid) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
    GROUP BY ve.voting_method, ve.party_voted
    ORDER BY ve.voting_method, ve.party_voted
""").fetchall()
for r in rows:
    print(f"  {r['voting_method']:15s} {r['party_voted']:12s} {r['cnt']:>6,}")

# Subtotals by method
print("\n--- Subtotals by voting method ---")
rows2 = conn.execute("""
    SELECT 
        ve.voting_method,
        COUNT(DISTINCT ve.vuid) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
    GROUP BY ve.voting_method
    ORDER BY ve.voting_method
""").fetchall()
for r in rows2:
    print(f"  {r['voting_method']:15s} {r['cnt']:>6,}")

# 3. Check for voters who appear in BOTH early-voting AND mail-in
print("\n--- Overlap: voters in both early-voting AND mail-in ---")
overlap = conn.execute("""
    SELECT 
        COUNT(DISTINCT ev.vuid) as cnt
    FROM voter_elections ev
    JOIN voter_elections mi ON ev.vuid = mi.vuid
        AND mi.election_date = '2026-03-03'
        AND mi.voting_method = 'mail-in'
    JOIN voters v ON ev.vuid = v.vuid
    WHERE ev.election_date = '2026-03-03'
      AND ev.voting_method = 'early-voting'
      AND v.county = 'Hidalgo'
""").fetchone()
print(f"  Overlap count: {overlap['cnt']}")

# 4. Check by source file to understand what was uploaded
print("\n--- By source file ---")
rows3 = conn.execute("""
    SELECT 
        ve.source_file,
        ve.voting_method,
        ve.party_voted,
        COUNT(*) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
    GROUP BY ve.source_file, ve.voting_method, ve.party_voted
    ORDER BY ve.voting_method, ve.party_voted, ve.source_file
""").fetchall()
for r in rows3:
    fn = r['source_file'] or '(none)'
    if len(fn) > 60:
        fn = fn[:57] + '...'
    print(f"  {r['voting_method']:15s} {r['party_voted']:12s} {r['cnt']:>6,}  {fn}")

# 5. What the API would show (grouped by voting method)
print("\n--- What /api/elections shows ---")
rows4 = conn.execute("""
    SELECT 
        ve.voting_method,
        COUNT(DISTINCT ve.vuid) as total,
        COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
        COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
    GROUP BY ve.voting_method
""").fetchall()
for r in rows4:
    print(f"  {r['voting_method']:15s}  total={r['total']:>6,}  DEM={r['dem']:>6,}  REP={r['rep']:>6,}")

# 6. Early-voting only (no mail-in)
print("\n--- Early-voting ONLY (excluding mail-in) ---")
ev_only = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as total,
        COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
        COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
      AND ve.voting_method = 'early-voting'
""").fetchone()
print(f"  Total: {ev_only['total']:>6,}  DEM: {ev_only['dem']:>6,}  REP: {ev_only['rep']:>6,}")

conn.close()
print("\n" + "=" * 70)
