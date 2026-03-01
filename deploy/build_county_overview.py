#!/usr/bin/env python3
"""Build just the county overview cache files (fast)."""
import sys, json, os, sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
OUTPUT_DIR = '/opt/whovoted/public/cache'

os.makedirs(OUTPUT_DIR, exist_ok=True)
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Get unique election_date + voting_method combos
rows = conn.execute("""
    SELECT DISTINCT election_date, voting_method
    FROM election_summary
    WHERE election_date IS NOT NULL
""").fetchall()

combos = set()
combos.add(('2026-03-03', 'early-voting'))
for r in rows:
    combos.add((r['election_date'], r['voting_method'] or None))

for ed, vm in sorted(combos):
    method_str = vm or 'all'
    where = "WHERE ve.election_date = ? AND ve.party_voted != '' AND ve.party_voted IS NOT NULL"
    params = [ed]
    if vm:
        where += " AND ve.voting_method = ?"
        params.append(vm)
    
    ov_rows = conn.execute(f"""
        SELECT v.county,
               ROUND(AVG(v.lat), 4) as lat,
               ROUND(AVG(v.lng), 4) as lng,
               COUNT(DISTINCT ve.vuid) as total,
               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where}
        AND v.geocoded = 1 AND v.lat IS NOT NULL
        GROUP BY v.county
        ORDER BY total DESC
    """, params).fetchall()
    
    counties_data = []
    for r in ov_rows:
        if r['county'] and r['lat']:
            counties_data.append({
                'county': r['county'], 'lat': float(r['lat']), 'lng': float(r['lng']),
                'total': r['total'], 'dem': r['dem'], 'rep': r['rep']
            })
    
    path = os.path.join(OUTPUT_DIR, f'county_overview_{ed}_{method_str}.json')
    with open(path, 'w') as f:
        json.dump({'success': True, 'counties': counties_data}, f, separators=(',', ':'))
    print(f"  {ed}/{method_str}: {len(counties_data)} counties")

conn.close()
print("Done!")
