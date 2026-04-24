#!/usr/bin/env python3
"""Generate campus report cards using actual McAllen ISD middle school zone boundaries."""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
MS_ZONES_PATH = '/opt/whovoted/public/data/mcallen_ms_zones.json'
CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_campus_reportcard.json'
ELECTION_DATE = '2026-05-10'
MCALLEN_ZIPS = ('78501','78502','78503','78504','78505')

def point_in_polygon(x, y, polygon):
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def point_in_multipolygon(lng, lat, geometry):
    if geometry['type'] == 'Polygon':
        return point_in_polygon(lng, lat, geometry['coordinates'][0])
    elif geometry['type'] == 'MultiPolygon':
        for poly in geometry['coordinates']:
            if point_in_polygon(lng, lat, poly[0]):
                return True
    return False

def grade(turnout_pct):
    if turnout_pct >= 5.0: return 'A'
    if turnout_pct >= 3.0: return 'B'
    if turnout_pct >= 2.0: return 'C'
    if turnout_pct >= 1.0: return 'D'
    return 'F'

# Friendly names
FRIENDLY = {
    'CATHAY MS': 'Cathey Middle School',
    'DELEON MS': 'De Leon Middle School',
    'FOSSUM': 'Fossum Middle School',
    'LINCOLN MS': 'Lincoln Middle School',
    'MORRIS MS': 'Morris Middle School',
    'TRAVIS MS': 'Travis Middle School',
}

def main():
    print("Generating campus report cards with real zone boundaries...")
    
    with open(MS_ZONES_PATH) as f:
        zones_data = json.load(f)
    
    zones = {}
    for feat in zones_data['features']:
        name = feat['properties']['NAME']
        zones[name] = {
            'name': FRIENDLY.get(name, name),
            'geometry': feat['geometry'],
            'registered': 0, 'voted': 0, 'dem': 0, 'rep_party': 0
        }
    print(f"Loaded {len(zones)} school zones")
    
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
    print(f"Processing {len(rows)} voters...")
    
    for lat, lng, voted, party in rows:
        for zname, z in zones.items():
            if point_in_multipolygon(lng, lat, z['geometry']):
                z['registered'] += 1
                if voted:
                    z['voted'] += 1
                    p = (party or '').lower()
                    if 'democrat' in p: z['dem'] += 1
                    elif 'republican' in p: z['rep_party'] += 1
                break
    
    campuses = []
    total_reg = total_voted = 0
    for zname in sorted(zones.keys()):
        z = zones[zname]
        reg, voted = z['registered'], z['voted']
        turnout = (voted / reg * 100) if reg > 0 else 0
        total_reg += reg; total_voted += voted
        campuses.append({
            'name': z['name'], 'registered': reg, 'voted': voted,
            'not_voted': reg - voted, 'dem': z['dem'], 'rep_party': z['rep_party'],
            'turnout_pct': round(turnout, 2), 'grade': grade(turnout)
        })
        print(f"  {z['name']}: {voted}/{reg} = {turnout:.2f}% → {grade(turnout)}")
    
    overall = (total_voted / total_reg * 100) if total_reg > 0 else 0
    data = {
        'campuses': campuses,
        'summary': {
            'total_registered': total_reg, 'total_voted': total_voted,
            'total_not_voted': total_reg - total_voted,
            'overall_turnout_pct': round(overall, 2), 'overall_grade': grade(overall)
        }
    }
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    print(f"\nOverall: {total_voted}/{total_reg} = {overall:.2f}% ({grade(overall)})")

if __name__ == '__main__':
    main()
