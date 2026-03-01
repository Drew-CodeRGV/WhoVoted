#!/usr/bin/env python3
"""Test alternative query approaches for get_election_datasets."""
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
    return rows

# Current approach
bench("Current: JOIN + GROUP BY + COUNT(DISTINCT)", """
    SELECT ve.election_date, ve.voting_method, ve.party_voted, v.county,
        COUNT(DISTINCT ve.vuid) as total_voters,
        COUNT(DISTINCT CASE WHEN v.geocoded = 1 THEN ve.vuid END) as geocoded_count
    FROM voter_elections ve INNER JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.party_voted != '' AND ve.party_voted IS NOT NULL
    GROUP BY ve.election_date, ve.party_voted, ve.voting_method, v.county
""")

# Alternative 1: Subquery approach — aggregate VE first, then join for county/geocoded
bench("Alt 1: Two-step with subquery", """
    SELECT ve_agg.election_date, ve_agg.voting_method, ve_agg.party_voted,
        v.county, COUNT(*) as total_voters,
        SUM(CASE WHEN v.geocoded = 1 THEN 1 ELSE 0 END) as geocoded_count
    FROM (
        SELECT DISTINCT vuid, election_date, election_year, election_type,
            voting_method, party_voted, source_file
        FROM voter_elections
        WHERE party_voted != '' AND party_voted IS NOT NULL
    ) ve_agg
    INNER JOIN voters v ON ve_agg.vuid = v.vuid
    GROUP BY ve_agg.election_date, ve_agg.party_voted, ve_agg.voting_method, v.county
""")

# Alternative 2: Use a temp table
conn.execute("DROP TABLE IF EXISTS _tmp_ve_unique")
t0 = time.time()
conn.execute("""
    CREATE TEMP TABLE _tmp_ve_unique AS
    SELECT DISTINCT vuid, election_date, election_year, election_type,
        voting_method, party_voted, source_file
    FROM voter_elections
    WHERE party_voted != '' AND party_voted IS NOT NULL
""")
elapsed1 = time.time() - t0
print(f"  {elapsed1*1000:>7.1f}ms  temp table created")

t0 = time.time()
rows = conn.execute("""
    SELECT t.election_date, t.voting_method, t.party_voted,
        v.county, COUNT(*) as total_voters,
        SUM(CASE WHEN v.geocoded = 1 THEN 1 ELSE 0 END) as geocoded_count
    FROM _tmp_ve_unique t
    INNER JOIN voters v ON t.vuid = v.vuid
    GROUP BY t.election_date, t.party_voted, t.voting_method, v.county
""").fetchall()
elapsed2 = time.time() - t0
print(f"  {elapsed2*1000:>7.1f}ms  {len(rows):>6,} rows  Alt 2: Temp table + JOIN")
print(f"  {(elapsed1+elapsed2)*1000:>7.1f}ms  total for Alt 2")

conn.close()
