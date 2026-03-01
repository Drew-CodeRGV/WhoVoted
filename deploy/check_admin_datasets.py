#!/usr/bin/env python3
"""Check what /admin/election-datasets returns."""
import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Replicate get_election_datasets
rows = conn.execute("""
    SELECT 
        ve.election_date,
        ve.election_year,
        ve.election_type,
        ve.voting_method,
        ve.party_voted,
        ve.source_file,
        COALESCE(v.county, 'Unknown') as county,
        COUNT(DISTINCT ve.vuid) as total_voters,
        SUM(CASE WHEN v.geocoded = 1 THEN 1 ELSE 0 END) as geocoded_count,
        SUM(CASE WHEN v.geocoded != 1 OR v.geocoded IS NULL THEN 1 ELSE 0 END) as ungeocoded_count,
        MIN(ve.created_at) as first_imported,
        MAX(ve.created_at) as last_updated
    FROM voter_elections ve
    LEFT JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.party_voted != '' AND ve.party_voted IS NOT NULL
    GROUP BY ve.election_date, ve.party_voted, ve.voting_method, COALESCE(v.county, 'Unknown')
    ORDER BY ve.election_date DESC, ve.party_voted, ve.voting_method
""").fetchall()

print(f"{'date':12s} {'county':8s} {'method':15s} {'party':12s} {'total':>6s} {'geo':>6s} {'ungeo':>6s} {'rate':>6s}  source")
print("-" * 120)
for r in rows:
    total = r['total_voters']
    geo = r['geocoded_count']
    ungeo = r['ungeocoded_count']
    rate = (geo / total * 100) if total > 0 else 0
    fn = (r['source_file'] or '—')[:40]
    flag = " ⚠️" if rate < 99.9 else ""
    print(f"{r['election_date']:12s} {r['county']:8s} {r['voting_method']:15s} {r['party_voted']:12s} "
          f"{total:>6,} {geo:>6,} {ungeo:>6,} {rate:>5.1f}%{flag}  {fn}")

# Check: is the issue that SUM counts duplicates?
print("\n\nDiagnostic: COUNT vs SUM for 2026 Hidalgo EV DEM")
diag = conn.execute("""
    SELECT 
        COUNT(*) as row_count,
        COUNT(DISTINCT ve.vuid) as unique_vuids,
        SUM(CASE WHEN v.geocoded = 1 THEN 1 ELSE 0 END) as sum_geocoded,
        COUNT(DISTINCT CASE WHEN v.geocoded = 1 THEN ve.vuid END) as distinct_geocoded
    FROM voter_elections ve
    LEFT JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03' AND ve.voting_method = 'early-voting'
      AND ve.party_voted = 'Democratic' AND COALESCE(v.county, 'Unknown') = 'Hidalgo'
""").fetchone()
print(f"  row_count={diag['row_count']}, unique_vuids={diag['unique_vuids']}, "
      f"sum_geocoded={diag['sum_geocoded']}, distinct_geocoded={diag['distinct_geocoded']}")

conn.close()
