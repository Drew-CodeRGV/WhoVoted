#!/usr/bin/env python3
"""Cache D5-area voters who voted in the bond but skipped the D5 city election."""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_bond_not_d5.json'

def point_in_polygon(x, y, ring):
    n = len(ring); inside = False; j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]; xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def point_in_geom(lng, lat, geom):
    if geom['type'] == 'Polygon': return point_in_polygon(lng, lat, geom['coordinates'][0])
    elif geom['type'] == 'MultiPolygon': return any(point_in_polygon(lng, lat, p[0]) for p in geom['coordinates'])
    return False

def main():
    print("Caching bond-not-D5 targets...")
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)
    hd41 = next(f for f in districts['features'] if f['properties'].get('district_id') == 'HD-41')
    hd41_geom = hd41['geometry']

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get D5 precincts
    d5_pcts = [r[0] for r in conn.execute("SELECT DISTINCT v.precinct FROM voters v INNER JOIN voter_elections ve ON v.vuid=ve.vuid WHERE ve.election_date='2026-05-02' AND v.precinct IS NOT NULL").fetchall()]
    ph = ','.join('?' * len(d5_pcts))

    rows = conn.execute(f"""
        SELECT v.vuid, v.lat, v.lng, v.precinct, v.address, v.city, v.zip,
               v.firstname, v.lastname, v.birth_year, v.sex, v.current_party
        FROM voters v
        INNER JOIN voter_elections ve_bond ON v.vuid = ve_bond.vuid
        WHERE ve_bond.election_date = '2026-05-10'
        AND v.precinct IN ({ph})
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
        AND v.vuid NOT IN (SELECT vuid FROM voter_elections WHERE election_date = '2026-05-02')
    """, d5_pcts).fetchall()

    voters = []
    vuids = []
    for row in rows:
        if not point_in_geom(row['lng'], row['lat'], hd41_geom):
            continue
        vuids.append(row['vuid'])
        voted_primary = conn.execute("SELECT 1 FROM voter_elections WHERE vuid=? AND election_date='2026-03-03'", (row['vuid'],)).fetchone()
        voters.append({
            'vuid': row['vuid'], 'lat': row['lat'], 'lng': row['lng'],
            'precinct': row['precinct'], 'address': row['address'], 'city': row['city'], 'zip': row['zip'],
            'name': f"{row['firstname'] or ''} {row['lastname'] or ''}".strip(),
            'birth_year': row['birth_year'], 'sex': row['sex'],
            'current_party': row['current_party'] or 'None',
            'voted_primary': bool(voted_primary),
            'hist': [],
        })

    # History
    vuid_to_idx = {v['vuid']: i for i, v in enumerate(voters)}
    for start in range(0, len(vuids), 500):
        chunk = vuids[start:start+500]
        p2 = ','.join('?' * len(chunk))
        for hr in conn.execute(f"SELECT vuid, election_date, party_voted FROM voter_elections WHERE vuid IN ({p2}) ORDER BY election_date", chunk).fetchall():
            idx = vuid_to_idx.get(hr['vuid'])
            if idx is not None and hr['party_voted']:
                letter = 'D' if 'democrat' in hr['party_voted'].lower() else 'R' if 'republican' in hr['party_voted'].lower() else 'O'
                voters[idx]['hist'].append({'y': (hr['election_date'] or '')[:4], 'p': letter})

    conn.close()

    dem = len([v for v in voters if v['current_party'] == 'Democratic'])
    rep = len([v for v in voters if v['current_party'] == 'Republican'])
    none = len([v for v in voters if v['current_party'] == 'None'])
    also_primary = len([v for v in voters if v['voted_primary']])

    data = {
        'voters': voters, 'count': len(voters),
        'dem_history': dem, 'rep_history': rep, 'no_history': none,
        'also_voted_primary': also_primary,
        'description': 'D5-area voters who voted in MISD Bond (May 10) but skipped D5 city election (May 2). Highly engaged — they vote, just missed the city race.',
    }
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    print(f"✓ {len(voters)} targets ({Path(CACHE_PATH).stat().st_size/1024:.0f} KB)")
    print(f"  Dem: {dem} | Rep: {rep} | None: {none} | Also primary: {also_primary}")

if __name__ == '__main__':
    main()
