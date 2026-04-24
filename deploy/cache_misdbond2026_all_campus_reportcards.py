#!/usr/bin/env python3
"""Generate campus report cards for MS, HS, and Elementary using GIS zone boundaries."""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-05-10'
MCALLEN_ZIPS = ('78501','78502','78503','78504','78505')
CACHE_DIR = '/opt/whovoted/public/cache'

def pip(x, y, poly):
    n = len(poly); inside = False; j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def pip_geom(lng, lat, geom):
    if geom['type'] == 'Polygon':
        return pip(lng, lat, geom['coordinates'][0])
    elif geom['type'] == 'MultiPolygon':
        return any(pip(lng, lat, p[0]) for p in geom['coordinates'])
    return False

def grade(t):
    if t >= 5: return 'A'
    if t >= 3: return 'B'
    if t >= 2: return 'C'
    if t >= 1: return 'D'
    return 'F'

def build_reportcard(zones_path, cache_path, voters, label):
    print(f"\n--- {label} ---")
    with open(zones_path) as f:
        data = json.load(f)
    
    zones = {}
    for feat in data['features']:
        name = feat['properties']['NAME']
        if name not in zones:
            zones[name] = {'geom': feat['geometry'], 'reg': 0, 'voted': 0, 'dem': 0, 'rep': 0}
        else:
            # Merge multi-part (like Memorial HS with 2 polygons)
            existing = zones[name]['geom']
            new = feat['geometry']
            if existing['type'] == 'Polygon' and new['type'] == 'Polygon':
                zones[name]['geom'] = {'type': 'MultiPolygon', 'coordinates': [existing['coordinates'], new['coordinates']]}
            elif existing['type'] == 'MultiPolygon':
                if new['type'] == 'Polygon':
                    existing['coordinates'].append(new['coordinates'])
                else:
                    existing['coordinates'].extend(new['coordinates'])
    
    print(f"Zones: {len(zones)}")
    
    for lat, lng, voted, party in voters:
        for zn, z in zones.items():
            if pip_geom(lng, lat, z['geom']):
                z['reg'] += 1
                if voted:
                    z['voted'] += 1
                    p = (party or '').lower()
                    if 'democrat' in p: z['dem'] += 1
                    elif 'republican' in p: z['rep'] += 1
                break
    
    campuses = []
    tr = tv = 0
    for name in sorted(zones.keys()):
        z = zones[name]
        t = (z['voted'] / z['reg'] * 100) if z['reg'] > 0 else 0
        tr += z['reg']; tv += z['voted']
        campuses.append({
            'name': name, 'registered': z['reg'], 'voted': z['voted'],
            'not_voted': z['reg'] - z['voted'], 'dem': z['dem'], 'rep_party': z['rep'],
            'turnout_pct': round(t, 2), 'grade': grade(t)
        })
        print(f"  {name}: {z['voted']}/{z['reg']} = {t:.2f}% → {grade(t)}")
    
    ov = (tv / tr * 100) if tr > 0 else 0
    result = {
        'campuses': campuses,
        'summary': {'total_registered': tr, 'total_voted': tv, 'total_not_voted': tr - tv,
                    'overall_turnout_pct': round(ov, 2), 'overall_grade': grade(ov)}
    }
    Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'w') as f:
        json.dump(result, f, separators=(',', ':'))
    print(f"Overall: {tv}/{tr} = {ov:.2f}% ({grade(ov)})")

def main():
    conn = sqlite3.connect(DB_PATH)
    ph = ','.join('?' * len(MCALLEN_ZIPS))
    rows = conn.execute(f"""
        SELECT v.lat, v.lng,
               CASE WHEN ve.vuid IS NOT NULL THEN 1 ELSE 0 END as voted,
               v.current_party
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL AND v.lng IS NOT NULL
    """, (ELECTION_DATE,) + MCALLEN_ZIPS).fetchall()
    conn.close()
    print(f"Loaded {len(rows)} voters")
    
    build_reportcard('/opt/whovoted/public/data/mcallen_ms_zones.json',
                     f'{CACHE_DIR}/misdbond2026_campus_reportcard.json', rows, 'Middle Schools')
    build_reportcard('/opt/whovoted/public/data/mcallen_hs_zones.json',
                     f'{CACHE_DIR}/misdbond2026_hs_reportcard.json', rows, 'High Schools')
    build_reportcard('/opt/whovoted/public/data/mcallen_elem_zones.json',
                     f'{CACHE_DIR}/misdbond2026_elem_reportcard.json', rows, 'Elementary Schools')

if __name__ == '__main__':
    main()
