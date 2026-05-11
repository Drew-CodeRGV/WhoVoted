#!/usr/bin/env python3
"""
Cache HD-41 voters STRICTLY inside the district boundary.
Uses geometric point-in-polygon check on each voter's lat/lng against the
official TLC PLANH2316 boundary. No voter outside the polygon is included.
"""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_voters.json'
ELECTION_DATE = '2026-03-03'

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
    print("Caching HD-41 voters (strict geometric filter)...")

    # Load HD-41 boundary
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)
    hd41 = next(f for f in districts['features'] if f['properties'].get('district_id') == 'HD-41')
    hd41_geom = hd41['geometry']

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get all voters who voted in the March primary AND are tagged HD-41
    rows = conn.execute("""
        SELECT v.vuid, v.lat, v.lng, v.precinct, v.address, v.city, v.zip,
               v.firstname, v.lastname, v.birth_year, v.sex,
               ve.party_voted, ve.voting_method
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ? AND v.state_house_district = 'HD-41'
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
    """, (ELECTION_DATE,)).fetchall()

    print(f"  Tagged HD-41: {len(rows)} voters")

    # Geometric filter: only keep voters whose lat/lng is inside the polygon
    voters = []
    vuids = []
    outside = 0
    for row in rows:
        if not point_in_geom(row['lng'], row['lat'], hd41_geom):
            outside += 1
            continue
        vuids.append(row['vuid'])
        voters.append({
            'vuid': row['vuid'],
            'lat': row['lat'], 'lng': row['lng'],
            'precinct': row['precinct'],
            'address': row['address'], 'city': row['city'], 'zip': row['zip'],
            'name': f"{row['firstname'] or ''} {row['lastname'] or ''}".strip(),
            'birth_year': row['birth_year'], 'sex': row['sex'],
            'party_voted': row['party_voted'],
            'voting_method': row['voting_method'],
            'hist': [],
        })

    print(f"  Inside boundary: {len(voters)} voters")
    print(f"  Filtered out (outside): {outside}")

    # Voting history (batched)
    if vuids:
        vuid_to_idx = {v['vuid']: i for i, v in enumerate(voters)}
        chunk_size = 500
        for start in range(0, len(vuids), chunk_size):
            chunk = vuids[start:start+chunk_size]
            ph = ','.join('?' * len(chunk))
            hist_rows = conn.execute(f"""
                SELECT vuid, election_date, party_voted
                FROM voter_elections WHERE vuid IN ({ph}) AND election_date != ?
                ORDER BY election_date
            """, chunk + [ELECTION_DATE]).fetchall()
            for hr in hist_rows:
                idx = vuid_to_idx.get(hr['vuid'])
                if idx is not None and hr['party_voted']:
                    letter = 'D' if 'democrat' in hr['party_voted'].lower() else 'R' if 'republican' in hr['party_voted'].lower() else 'O'
                    voters[idx]['hist'].append({'y': (hr['election_date'] or '')[:4], 'p': letter})

    conn.close()

    methods = {}
    for v in voters:
        m = v.get('voting_method') or 'unknown'
        methods[m] = methods.get(m, 0) + 1

    data = {'voters': voters, 'count': len(voters), 'method_breakdown': methods, 'election_date': ELECTION_DATE}
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    print(f"✓ Cached {len(voters)} voters ({Path(CACHE_PATH).stat().st_size/1024/1024:.1f} MB)")

if __name__ == '__main__':
    main()
