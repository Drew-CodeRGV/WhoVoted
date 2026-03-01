#!/usr/bin/env python3
"""Checkpoint WAL, add indexes, and benchmark heatmap query."""
import sqlite3
import time

DB = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB, timeout=60)
conn.execute("PRAGMA busy_timeout=60000")
conn.row_factory = sqlite3.Row

# Step 1: Checkpoint the WAL file (merge it back into main DB)
print("Checkpointing WAL...")
t0 = time.time()
result = conn.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone()
print(f"  WAL checkpoint result: {list(result)} in {time.time()-t0:.1f}s")

import os
wal_path = DB + '-wal'
if os.path.exists(wal_path):
    print(f"  WAL file size after checkpoint: {os.path.getsize(wal_path) / 1024 / 1024:.1f}MB")

# Step 2: Add optimized indexes
print("\nAdding indexes...")
t0 = time.time()

conn.execute("CREATE INDEX IF NOT EXISTS idx_ve_vuid_date_party_method ON voter_elections(vuid, election_date DESC, party_voted, voting_method)")
print(f"  idx_ve_vuid_date_party_method: {time.time()-t0:.1f}s")

t1 = time.time()
conn.execute("CREATE INDEX IF NOT EXISTS idx_voters_county_geo ON voters(county, geocoded, lat, lng)")
print(f"  idx_voters_county_geo: {time.time()-t1:.1f}s")

t2 = time.time()
conn.execute("CREATE INDEX IF NOT EXISTS idx_ve_date_party_vuid ON voter_elections(election_date, party_voted, vuid)")
print(f"  idx_ve_date_party_vuid: {time.time()-t2:.1f}s")

conn.commit()
print(f"  Total index time: {time.time()-t0:.1f}s")

# Step 3: ANALYZE to update query planner statistics
print("\nRunning ANALYZE...")
t0 = time.time()
conn.execute("ANALYZE")
conn.commit()
print(f"  ANALYZE done in {time.time()-t0:.1f}s")

# Step 4: Benchmark the heatmap query
print("\n=== Benchmarking heatmap query ===")

# Main query
t0 = time.time()
rows = conn.execute("""
    SELECT ve.vuid, v.lat, v.lng, ve.party_voted, v.sex, v.birth_year
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
      AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
      AND v.geocoded = 1 AND v.lat IS NOT NULL AND v.lng IS NOT NULL
      AND ve.voting_method = 'early-voting'
""").fetchall()
t1 = time.time()
print(f"  Main query: {len(rows)} rows in {t1-t0:.2f}s")

vuids = [r['vuid'] for r in rows]

# Previous party via temp table + JOIN
conn.execute("CREATE TEMP TABLE IF NOT EXISTS tmp_vuids(vuid TEXT PRIMARY KEY)")
conn.execute("DELETE FROM tmp_vuids")
for i in range(0, len(vuids), 999):
    chunk = vuids[i:i+999]
    conn.executemany("INSERT OR IGNORE INTO tmp_vuids(vuid) VALUES(?)", [(v,) for v in chunk])
t2 = time.time()
print(f"  Temp table insert: {t2-t1:.2f}s")

prev_rows = conn.execute("""
    SELECT ve.vuid, ve.party_voted
    FROM voter_elections ve
    INNER JOIN tmp_vuids t ON ve.vuid = t.vuid
    WHERE ve.election_date = (
        SELECT MAX(ve2.election_date) FROM voter_elections ve2
        WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
          AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
    )
    AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
""").fetchall()
t3 = time.time()
print(f"  Previous party: {len(prev_rows)} rows in {t3-t2:.2f}s")

prior_rows = conn.execute("""
    SELECT DISTINCT ve.vuid FROM voter_elections ve
    INNER JOIN tmp_vuids t ON ve.vuid = t.vuid
    WHERE ve.election_date < '2026-03-03'
      AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
""").fetchall()
t4 = time.time()
print(f"  Prior voters: {len(prior_rows)} rows in {t4-t3:.2f}s")

print(f"\n  TOTAL heatmap build: {t4-t0:.2f}s")

# Step 5: Benchmark election-stats query
print("\n=== Benchmarking election-stats ===")
t0 = time.time()
row = conn.execute("""
    SELECT
        COUNT(DISTINCT ve.vuid) as total,
        COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
        COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep,
        COUNT(DISTINCT CASE WHEN v.geocoded = 1 THEN ve.vuid END) as geocoded
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
      AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
      AND ve.voting_method = 'early-voting'
""").fetchone()
t1 = time.time()
print(f"  Basic stats: total={row['total']}, dem={row['dem']}, rep={row['rep']} in {t1-t0:.2f}s")

conn.execute("DROP TABLE IF EXISTS tmp_vuids")
conn.close()
