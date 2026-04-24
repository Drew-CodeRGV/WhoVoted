#!/usr/bin/env python3
"""Generate SMD report card for McAllen ISD Bond 2026 using city commission district boundaries."""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
SMD_PATH = '/opt/whovoted/public/data/mcallen_smd.json'
CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_reportcard.json'
ELECTION_DATE = '2026-05-10'
MCALLEN_ZIPS = ('78501','78502','78503','78504','78505')

def point_in_polygon(x, y, polygon):
    """Ray casting algorithm for point-in-polygon."""
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
    """Check if point is in a GeoJSON geometry (Polygon or MultiPolygon)."""
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

def main():
    print("Generating SMD report card for McAllen ISD Bond 2026...")
    
    # Load SMD boundaries
    with open(SMD_PATH) as f:
        smd_data = json.load(f)
    
    districts = {}
    for feat in smd_data['features']:
        props = feat['properties']
        name = props.get('NAME', '')
        num = name.replace('District ', '') if name.startswith('District ') else name
        districts[num] = {
            'name': name,
            'rep': props.get('REPNAME', ''),
            'geometry': feat['geometry'],
            'registered': 0,
            'voted': 0,
            'dem': 0,
            'rep_party': 0
        }
    
    print(f"Loaded {len(districts)} SMD boundaries")
    
    # Get all McAllen voters
    conn = sqlite3.connect(DB_PATH)
    ph = ','.join('?' * len(MCALLEN_ZIPS))
    
    rows = conn.execute(f"""
        SELECT v.vuid, v.lat, v.lng,
               CASE WHEN ve.vuid IS NOT NULL THEN 1 ELSE 0 END as voted,
               v.current_party
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.zip IN ({ph})
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
    """, (ELECTION_DATE,) + MCALLEN_ZIPS).fetchall()
    
    print(f"Processing {len(rows)} voters...")
    
    unassigned = 0
    for vuid, lat, lng, voted, party in rows:
        assigned = False
        for num, dist in districts.items():
            if point_in_multipolygon(lng, lat, dist['geometry']):
                dist['registered'] += 1
                if voted:
                    dist['voted'] += 1
                    p = (party or '').lower()
                    if 'democrat' in p:
                        dist['dem'] += 1
                    elif 'republican' in p:
                        dist['rep_party'] += 1
                assigned = True
                break
        if not assigned:
            unassigned += 1
    
    conn.close()
    
    # Build report card
    report = []
    total_reg = 0
    total_voted = 0
    for num in sorted(districts.keys()):
        d = districts[num]
        reg = d['registered']
        voted = d['voted']
        turnout = (voted / reg * 100) if reg > 0 else 0
        total_reg += reg
        total_voted += voted
        report.append({
            'district': num,
            'name': d['name'],
            'rep': d['rep'],
            'registered': reg,
            'voted': voted,
            'not_voted': reg - voted,
            'dem': d['dem'],
            'rep_party': d['rep_party'],
            'turnout_pct': round(turnout, 2),
            'grade': grade(turnout)
        })
        print(f"  {d['name']} ({d['rep']}): {voted}/{reg} = {turnout:.2f}% → {grade(turnout)}")
    
    overall_turnout = (total_voted / total_reg * 100) if total_reg > 0 else 0
    data = {
        'districts': report,
        'summary': {
            'total_registered': total_reg,
            'total_voted': total_voted,
            'total_not_voted': total_reg - total_voted,
            'overall_turnout_pct': round(overall_turnout, 2),
            'overall_grade': grade(overall_turnout),
            'unassigned_voters': unassigned
        }
    }
    
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    
    print(f"\nOverall: {total_voted}/{total_reg} = {overall_turnout:.2f}% (Grade: {grade(overall_turnout)})")
    print(f"Unassigned (outside all SMDs): {unassigned}")

if __name__ == '__main__':
    main()
