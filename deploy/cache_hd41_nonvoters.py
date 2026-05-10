#!/usr/bin/env python3
"""Cache heatmap data for registered HD-41 voters who have NOT voted in the 2026 primary."""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_nonvoters.json'
# HD-41 runoff — May 26, 2026
ELECTION_DATE = '2026-05-26'
DISTRICT = 'HD-41'

def main():
    print(f"Caching non-voter heatmap for {DISTRICT}...")
    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute("""
        SELECT v.lat, v.lng
        FROM voters v
        WHERE v.state_house_district = ?
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
        AND v.vuid NOT IN (
            SELECT ve.vuid FROM voter_elections ve WHERE ve.election_date = ?
        )
    """, (DISTRICT, ELECTION_DATE)).fetchall()

    points = [[r[0], r[1]] for r in rows]
    conn.close()

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump({'points': points, 'count': len(points)}, f, separators=(',', ':'))

    print(f"✓ Cached {len(points)} non-voter locations ({Path(CACHE_PATH).stat().st_size / 1024:.0f} KB)")

if __name__ == '__main__':
    main()
