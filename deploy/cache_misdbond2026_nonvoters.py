#!/usr/bin/env python3
"""Cache heatmap data for registered McAllen voters who have NOT voted in the bond election."""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_nonvoters.json'
ELECTION_DATE = '2026-05-10'
MCALLEN_ZIPS = ('78501','78502','78503','78504','78505')

def main():
    print("Caching non-voter heatmap for McAllen ISD Bond 2026...")
    conn = sqlite3.connect(DB_PATH)
    ph = ','.join('?' * len(MCALLEN_ZIPS))
    
    rows = conn.execute(f"""
        SELECT v.lat, v.lng
        FROM voters v
        WHERE v.zip IN ({ph})
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
        AND v.vuid NOT IN (
            SELECT ve.vuid FROM voter_elections ve WHERE ve.election_date = ?
        )
    """, MCALLEN_ZIPS + (ELECTION_DATE,)).fetchall()
    
    points = [[r[0], r[1]] for r in rows]
    conn.close()
    
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump({'points': points, 'count': len(points)}, f, separators=(',', ':'))
    
    print(f"Cached {len(points)} non-voter locations ({Path(CACHE_PATH).stat().st_size / 1024:.0f} KB)")

if __name__ == '__main__':
    main()
