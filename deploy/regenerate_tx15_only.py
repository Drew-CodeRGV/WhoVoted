#!/usr/bin/env python3
"""Regenerate TX-15 district cache only."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')

import sqlite3
import json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_DIR = '/opt/whovoted/public/cache'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("Regenerating TX-15 Congressional District cache...")

# Get TX-15 stats
stats = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as total,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep,
        SUM(CASE WHEN ve.is_new_voter = 1 THEN 1 ELSE 0 END) as new_total,
        SUM(CASE WHEN ve.is_new_voter = 1 AND ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as new_dem,
        SUM(CASE WHEN ve.is_new_voter = 1 AND ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as new_rep
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND v.tx_cong_district = '15'
""").fetchone()

# Party switchers
flips = conn.execute("""
    SELECT 
        ve_cur.party_voted as to_party,
        ve_prev.party_voted as from_party,
        COUNT(*) as cnt
    FROM voter_elections ve_cur
    JOIN voter_elections ve_prev ON ve_cur.vuid = ve_prev.vuid
    JOIN voters v ON ve_cur.vuid = v.vuid
    WHERE ve_cur.election_date = '2026-03-03'
      AND v.tx_cong_district = '15'
      AND ve_prev.election_date = (
          SELECT MAX(ve2.election_date) 
          FROM voter_elections ve2
          WHERE ve2.vuid = ve_cur.vuid 
            AND ve2.election_date < '2026-03-03'
            AND ve2.party_voted IN ('Democratic', 'Republican')
      )
      AND ve_cur.party_voted != ve_prev.party_voted
      AND ve_cur.party_voted IN ('Democratic', 'Republican')
      AND ve_prev.party_voted IN ('Democratic', 'Republican')
    GROUP BY ve_cur.party_voted, ve_prev.party_voted
""").fetchall()

r2d = sum(r['cnt'] for r in flips if r['from_party'] == 'Republican' and r['to_party'] == 'Democratic')
d2r = sum(r['cnt'] for r in flips if r['from_party'] == 'Democratic' and r['to_party'] == 'Republican')

# County breakdown
counties = conn.execute("""
    SELECT 
        v.county,
        COUNT(DISTINCT ve.vuid) as total,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND v.tx_cong_district = '15'
    GROUP BY v.county
    ORDER BY total DESC
""").fetchall()

county_breakdown = {}
for c in counties:
    county_breakdown[c['county']] = {
        'total': c['total'],
        'dem': c['dem'],
        'rep': c['rep']
    }

report = {
    'district_id': 'TX-15',
    'district_name': 'TX-15 Congressional District',
    'total': stats['total'],
    'dem': stats['dem'],
    'rep': stats['rep'],
    'dem_share': round(stats['dem'] / stats['total'] * 100, 1) if stats['total'] > 0 else 0,
    'new_total': stats['new_total'],
    'new_dem': stats['new_dem'],
    'new_rep': stats['new_rep'],
    'r2d': r2d,
    'd2r': d2r,
    'county_breakdown': county_breakdown,
    'generated_at': __import__('time').time()
}

# Save with both possible filenames
for name in ['TX-15_Congressional_District', 'TX-15_Congressional_District_(PlanC2333)']:
    cache_file = Path(CACHE_DIR) / f'district_report_{name}.json'
    with open(cache_file, 'w') as f:
        json.dump(report, f, separators=(',', ':'))
    print(f"✓ Saved: {cache_file.name}")

print(f"\nTX-15 Stats:")
print(f"  Total: {report['total']:,}")
print(f"  New voters: {report['new_total']:,} ({report['new_total']/report['total']*100:.1f}%)")
print(f"  Democratic: {report['dem']:,} ({report['dem_share']}%)")
print(f"  Republican: {report['rep']:,}")

conn.close()
