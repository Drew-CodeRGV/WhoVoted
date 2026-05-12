#!/usr/bin/env python3
"""
Cache HD-41 voters who voted in the McAllen ISD Bond but NOT in the March primary.
These are mobilization targets for the runoff — proven voters who skipped the primary.
"""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_bond_targets.json'

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
    print("Caching HD-41 bond-not-primary targets...")

    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)
    hd41 = next(f for f in districts['features'] if f['properties'].get('district_id') == 'HD-41')
    hd41_geom = hd41['geometry']

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    rows = conn.execute("""
        SELECT v.vuid, v.lat, v.lng, v.precinct, v.address, v.city, v.zip,
               v.firstname, v.lastname, v.birth_year, v.sex, v.current_party
        FROM voters v
        INNER JOIN voter_elections ve_bond ON v.vuid = ve_bond.vuid
        WHERE ve_bond.election_date = '2026-05-10'
        AND v.state_house_district = 'HD-41'
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
        AND v.vuid NOT IN (
            SELECT vuid FROM voter_elections WHERE election_date = '2026-03-03'
        )
    """).fetchall()

    # Geometric filter
    voters = []
    for row in rows:
        if not point_in_geom(row['lng'], row['lat'], hd41_geom):
            continue
        voters.append({
            'vuid': row['vuid'],
            'lat': row['lat'], 'lng': row['lng'],
            'precinct': row['precinct'],
            'address': row['address'], 'city': row['city'], 'zip': row['zip'],
            'name': f"{row['firstname'] or ''} {row['lastname'] or ''}".strip(),
            'birth_year': row['birth_year'], 'sex': row['sex'],
            'current_party': row['current_party'] or 'None',
        })

    conn.close()

    # Stats
    dem = len([v for v in voters if v['current_party'] == 'Democratic'])
    rep = len([v for v in voters if v['current_party'] == 'Republican'])
    none = len([v for v in voters if v['current_party'] == 'None'])

    data = {
        'voters': voters,
        'count': len(voters),
        'dem_history': dem,
        'rep_history': rep,
        'no_history': none,
        'description': 'Voted in McAllen ISD Bond (May 10) but NOT in March 3 Primary. Proven voters who skipped the HD-41 race.',
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    print(f"✓ {len(voters)} bond-not-primary targets ({Path(CACHE_PATH).stat().st_size/1024:.0f} KB)")
    print(f"  Dem history: {dem} | Rep history: {rep} | No history: {none}")

if __name__ == '__main__':
    main()
