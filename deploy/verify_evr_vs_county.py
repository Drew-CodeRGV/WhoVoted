#!/usr/bin/env python3
"""
Verify EVR (state-level) data against county-level data for Hidalgo County.

Compares:
1. Total voter counts by party and method
2. VUID overlap — are the same voters in both sources?
3. Any voters in county data but NOT in state data (would indicate data loss)
4. Data source breakdown
"""
import sqlite3
from collections import defaultdict

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=" * 70)
print("EVR vs County Data Verification — Hidalgo County 2026 Primary")
print("=" * 70)

# 1. Overall counts by data_source
print("\n--- 1. Record counts by data_source ---")
rows = conn.execute("""
    SELECT ve.data_source, ve.party_voted, ve.voting_method, COUNT(*) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo'
      AND ve.election_date = '2026-03-03'
    GROUP BY ve.data_source, ve.party_voted, ve.voting_method
    ORDER BY ve.data_source, ve.party_voted, ve.voting_method
""").fetchall()
for r in rows:
    print(f"  {r['data_source'] or '(empty)':20s} | {r['party_voted']:12s} | {r['voting_method']:15s} | {r['cnt']:>8,}")

# 2. Unique VUIDs by source for Hidalgo early-voting
print("\n--- 2. Unique VUIDs by source (Hidalgo, early-voting, 2026) ---")
for party in ['Republican', 'Democratic']:
    print(f"\n  {party}:")
    
    # County-upload VUIDs
    county_vuids = set(r[0] for r in conn.execute("""
        SELECT DISTINCT ve.vuid FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
          AND ve.party_voted = ? AND ve.voting_method = 'early-voting'
          AND ve.data_source = 'county-upload'
    """, (party,)).fetchall())
    
    # State (EVR) VUIDs
    evr_vuids = set(r[0] for r in conn.execute("""
        SELECT DISTINCT ve.vuid FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
          AND ve.party_voted = ? AND ve.voting_method = 'early-voting'
          AND ve.data_source = 'tx-sos-evr'
    """, (party,)).fetchall())
    
    # State voter data upload VUIDs
    svd_vuids = set(r[0] for r in conn.execute("""
        SELECT DISTINCT ve.vuid FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
          AND ve.party_voted = ? AND ve.voting_method = 'early-voting'
          AND ve.data_source = 'state-voter-data'
    """, (party,)).fetchall())
    
    # All VUIDs regardless of source
    all_vuids = set(r[0] for r in conn.execute("""
        SELECT DISTINCT ve.vuid FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
          AND ve.party_voted = ? AND ve.voting_method = 'early-voting'
    """, (party,)).fetchall())
    
    print(f"    County-upload VUIDs:     {len(county_vuids):>8,}")
    print(f"    TX SOS EVR VUIDs:        {len(evr_vuids):>8,}")
    print(f"    State-voter-data VUIDs:  {len(svd_vuids):>8,}")
    print(f"    Total unique VUIDs:      {len(all_vuids):>8,}")
    
    if county_vuids and evr_vuids:
        overlap = county_vuids & evr_vuids
        county_only = county_vuids - evr_vuids
        evr_only = evr_vuids - county_vuids
        print(f"    Overlap (both sources):  {len(overlap):>8,}")
        print(f"    County-only (NOT in EVR):{len(county_only):>8,}")
        print(f"    EVR-only (NOT in county):{len(evr_only):>8,}")
        
        if county_only:
            print(f"    ⚠️  {len(county_only)} voters in county data but missing from state data!")
            # Show a few examples
            samples = list(county_only)[:5]
            for vuid in samples:
                row = conn.execute("SELECT firstname, lastname FROM voters WHERE vuid = ?", (vuid,)).fetchone()
                if row:
                    print(f"       Example: VUID {vuid} — {row['lastname']}, {row['firstname']}")
        else:
            print(f"    ✅ All county voters found in state data")

# 3. Check vote_date coverage
print("\n--- 3. vote_date coverage ---")
rows = conn.execute("""
    SELECT ve.data_source,
           COUNT(*) as total,
           SUM(CASE WHEN ve.vote_date IS NOT NULL AND ve.vote_date != '' THEN 1 ELSE 0 END) as has_date
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
    GROUP BY ve.data_source
""").fetchall()
for r in rows:
    pct = (r['has_date'] / r['total'] * 100) if r['total'] > 0 else 0
    print(f"  {r['data_source'] or '(empty)':20s} | {r['has_date']:>8,} / {r['total']:>8,} have vote_date ({pct:.1f}%)")

# 4. Daily vote_date distribution for EVR data
print("\n--- 4. Daily vote counts (EVR, Hidalgo, Republican) ---")
rows = conn.execute("""
    SELECT ve.vote_date, COUNT(*) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
      AND ve.data_source = 'tx-sos-evr' AND ve.party_voted = 'Republican'
      AND ve.vote_date IS NOT NULL AND ve.vote_date != ''
    GROUP BY ve.vote_date
    ORDER BY ve.vote_date
""").fetchall()
for r in rows:
    print(f"  {r['vote_date']}  {r['cnt']:>6,}")

print("\n--- 5. Statewide totals by party (EVR data) ---")
rows = conn.execute("""
    SELECT ve.party_voted, ve.voting_method, COUNT(DISTINCT ve.vuid) as unique_voters
    FROM voter_elections ve
    WHERE ve.election_date = '2026-03-03'
      AND ve.data_source = 'tx-sos-evr'
    GROUP BY ve.party_voted, ve.voting_method
    ORDER BY ve.party_voted, ve.voting_method
""").fetchall()
for r in rows:
    print(f"  {r['party_voted']:12s} | {r['voting_method']:15s} | {r['unique_voters']:>10,} unique voters")

print("\n" + "=" * 70)
print("Done!")
conn.close()
