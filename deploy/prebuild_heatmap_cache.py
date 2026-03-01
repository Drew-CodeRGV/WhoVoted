#!/usr/bin/env python3
"""Pre-build static heatmap + stats JSON files for fast serving.

Run this after any data import (EVR scraper, county upload, etc.)
to regenerate the cache files that the API serves directly.

Usage: /opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/prebuild_heatmap_cache.py
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')

import json
import time
import os
import sqlite3

OUTPUT_DIR = '/opt/whovoted/public/cache'
DB_PATH = '/opt/whovoted/data/whovoted.db'

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    import database as db
    
    # Get all datasets from election_summary
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT DISTINCT county, election_date, voting_method
        FROM election_summary
        WHERE election_date IS NOT NULL
        ORDER BY election_date DESC
    """).fetchall()
    conn.close()
    
    datasets = set()
    datasets.add(('Hidalgo', '2026-03-03', 'early-voting'))
    for r in rows:
        if r['county'] and r['election_date']:
            datasets.add((r['county'], r['election_date'], r['voting_method'] or None))
    
    print(f"Building cache for {len(datasets)} datasets...")
    total_t = time.time()
    
    for county, election_date, voting_method in sorted(datasets):
        method_str = voting_method or 'all'
        label = f"{county}/{election_date}/{method_str}"
        
        try:
            t0 = time.time()
            
            # Heatmap
            points = db.get_voters_heatmap(county, election_date, voting_method)
            hm_data = json.dumps({'points': points, 'count': len(points)}, separators=(',', ':'))
            hm_path = os.path.join(OUTPUT_DIR, f'heatmap_{county}_{election_date}_{method_str}.json')
            with open(hm_path, 'w') as f:
                f.write(hm_data)
            
            # Stats
            stats = db.get_election_stats(county, election_date, None, voting_method)
            stats_data = json.dumps({'success': True, 'stats': stats}, separators=(',', ':'))
            stats_path = os.path.join(OUTPUT_DIR, f'stats_{county}_{election_date}_{method_str}.json')
            with open(stats_path, 'w') as f:
                f.write(stats_data)
            
            size_kb = len(hm_data) / 1024
            print(f"  {label}: {len(points)} pts, {size_kb:.0f}KB in {time.time()-t0:.1f}s")
        except Exception as e:
            print(f"  {label}: FAILED - {e}")
    
    print(f"\nDone in {time.time()-total_t:.1f}s. Files in {OUTPUT_DIR}")

    # Build county overview files (one per election_date + voting_method)
    print("\nBuilding county overview files...")
    overview_dates = set()
    for county, election_date, voting_method in sorted(datasets):
        method_str = voting_method or 'all'
        overview_dates.add((election_date, method_str, voting_method))
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    for ed, method_str, vm in sorted(overview_dates):
        try:
            where = "WHERE ve.election_date = ? AND ve.party_voted != '' AND ve.party_voted IS NOT NULL"
            params = [ed]
            if vm:
                where += " AND ve.voting_method = ?"
                params.append(vm)
            rows = conn.execute(f"""
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
            for r in rows:
                if r['county'] and r['lat']:
                    counties_data.append({'county': r['county'], 'lat': float(r['lat']), 'lng': float(r['lng']),
                                          'total': r['total'], 'dem': r['dem'], 'rep': r['rep']})
            ov_path = os.path.join(OUTPUT_DIR, f'county_overview_{ed}_{method_str}.json')
            with open(ov_path, 'w') as f:
                json.dump({'success': True, 'counties': counties_data}, f, separators=(',', ':'))
            print(f"  county_overview_{ed}_{method_str}: {len(counties_data)} counties")
        except Exception as e:
            print(f"  county_overview_{ed}_{method_str}: FAILED - {e}")
    conn.close()

if __name__ == '__main__':
    main()
