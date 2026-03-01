#!/usr/bin/env python3
"""Benchmark the key queries that run on initial page load."""
import sqlite3
import time

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

def bench(label, sql, params=()):
    t0 = time.time()
    rows = conn.execute(sql, params).fetchall()
    elapsed = time.time() - t0
    print(f"  {elapsed*1000:>7.1f}ms  {len(rows):>6,} rows  {label}")
    return elapsed

print("=" * 70)
print("QUERY BENCHMARKS")
print("=" * 70)

total = 0

# 1. /api/elections — get_election_datasets
total += bench("/api/elections (get_election_datasets)", """
    SELECT ve.election_date, ve.election_year, ve.election_type, ve.voting_method,
        ve.party_voted, ve.source_file, v.county,
        COUNT(DISTINCT ve.vuid) as total_voters,
        COUNT(DISTINCT CASE WHEN v.geocoded = 1 THEN ve.vuid END) as geocoded_count,
        COUNT(DISTINCT CASE WHEN v.geocoded != 1 OR v.geocoded IS NULL THEN ve.vuid END) as ungeocoded_count,
        MIN(ve.created_at) as first_imported, MAX(ve.created_at) as last_updated
    FROM voter_elections ve INNER JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.party_voted != '' AND ve.party_voted IS NOT NULL
    GROUP BY ve.election_date, ve.party_voted, ve.voting_method, v.county
    ORDER BY ve.election_date DESC, ve.party_voted, ve.voting_method
""")

# 2. /api/election-stats — for the default dataset
total += bench("/api/election-stats (Hidalgo 2026)", """
    SELECT COUNT(DISTINCT ve.vuid) as total,
        COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
        COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep,
        COUNT(DISTINCT CASE WHEN v.geocoded = 1 THEN ve.vuid END) as geocoded
    FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
""")

# 3. /api/election-stats flip detection — optimized with CTE
total += bench("/api/election-stats flips (Hidalgo 2026)", """
    WITH prev AS (
        SELECT vuid, party_voted,
               ROW_NUMBER() OVER (PARTITION BY vuid ORDER BY election_date DESC) as rn
        FROM voter_elections
        WHERE election_date IN ('2024-03-05','2022-03-01','2016-03-01')
          AND party_voted != '' AND party_voted IS NOT NULL
    )
    SELECT
        ve_cur.party_voted as cur_party,
        prev.party_voted as prev_party,
        COUNT(DISTINCT ve_cur.vuid) as cnt
    FROM voter_elections ve_cur
    JOIN voters v ON ve_cur.vuid = v.vuid
    JOIN prev ON ve_cur.vuid = prev.vuid AND prev.rn = 1
    WHERE v.county = 'Hidalgo' AND ve_cur.election_date = '2026-03-03'
      AND ve_cur.party_voted != prev.party_voted
      AND ve_cur.party_voted != '' AND ve_cur.party_voted IS NOT NULL
    GROUP BY ve_cur.party_voted, prev.party_voted
""")

# 4. /api/election-stats new voters — optimized with NOT EXISTS
total += bench("/api/election-stats new voters (Hidalgo 2026)", """
    SELECT COUNT(DISTINCT ve.vuid) as new_count
    FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
      AND NOT EXISTS (
          SELECT 1 FROM voter_elections ve_old
          WHERE ve_old.vuid = ve.vuid
            AND ve_old.election_date < '2026-03-03'
            AND ve_old.party_voted != '' AND ve_old.party_voted IS NOT NULL)
""")

# 5. /api/voters — the big one (map data)
total += bench("/api/voters (Hidalgo 2026 early-voting, no bounds)", """
    SELECT DISTINCT ve.vuid, v.firstname, v.lastname, v.address, v.precinct,
        v.lat, v.lng, v.geocoded, v.sex, v.birth_year,
        ve.party_voted, ve.voting_method, ve.election_date
    FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03' AND ve.voting_method = 'early-voting'
""")

# 6. /api/voters with bounds (typical map viewport)
total += bench("/api/voters (Hidalgo 2026 EV, bounded viewport)", """
    SELECT DISTINCT ve.vuid, v.firstname, v.lastname, v.address, v.precinct,
        v.lat, v.lng, v.geocoded, v.sex, v.birth_year,
        ve.party_voted, ve.voting_method, ve.election_date
    FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03' AND ve.voting_method = 'early-voting'
      AND v.lat BETWEEN 26.0 AND 26.5 AND v.lng BETWEEN -98.5 AND -98.0
""")

# 7. Check existing indexes
print("\n--- Existing Indexes ---")
idxs = conn.execute("SELECT name, tbl_name, sql FROM sqlite_master WHERE type='index' ORDER BY tbl_name, name").fetchall()
for idx in idxs:
    print(f"  {idx['tbl_name']:20s}  {idx['name']:40s}  {(idx['sql'] or '(auto)')[:60]}")

# 8. Table sizes
print("\n--- Table Sizes ---")
for tbl in ['voters', 'voter_elections', 'geocoding_cache']:
    row = conn.execute(f"SELECT COUNT(*) as cnt FROM {tbl}").fetchone()
    print(f"  {tbl:20s}  {row['cnt']:>10,} rows")

print(f"\n--- Total query time: {total*1000:.0f}ms ---")
conn.close()
