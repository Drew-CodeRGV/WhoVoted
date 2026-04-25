#!/usr/bin/env python3
"""Cache demographic breakdown for McAllen ISD Bond 2026 voters, with per-zone breakdowns."""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_demographics.json'
ELECTION_DATE = '2026-05-10'
MCALLEN_ZIPS = ('78501','78502','78503','78504','78505')
CURRENT_YEAR = 2026

SMD_PATH = '/opt/whovoted/public/data/mcallen_smd.json'
MS_PATH = '/opt/whovoted/public/data/mcallen_ms_zones.json'
HS_PATH = '/opt/whovoted/public/data/mcallen_hs_zones.json'

def pip(x, y, poly):
    n = len(poly); inside = False; j = n - 1
    for i in range(n):
        xi, yi = poly[i]; xj, yj = poly[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def pip_geom(lng, lat, geom):
    if geom['type'] == 'Polygon': return pip(lng, lat, geom['coordinates'][0])
    elif geom['type'] == 'MultiPolygon': return any(pip(lng, lat, p[0]) for p in geom['coordinates'])
    return False

def age_bucket(by):
    if not by or by < 1900: return None
    age = CURRENT_YEAR - by
    if age < 18: return None
    if age <= 25: return '18-25'
    if age <= 35: return '26-35'
    if age <= 45: return '36-45'
    if age <= 55: return '46-55'
    if age <= 65: return '56-65'
    return '65+'

AGE_GROUPS = ['18-25','26-35','36-45','46-55','56-65','65+']

def empty_demo():
    return {
        'age': {g: 0 for g in AGE_GROUPS}, 'reg_age': {g: 0 for g in AGE_GROUPS},
        'gender': {'M': 0, 'F': 0}, 'reg_gender': {'M': 0, 'F': 0},
        'party': {'Democratic': 0, 'Republican': 0, 'Other': 0},
        'dates': {}, 'method_dates': {},
        'methods': {'early-voting': 0, 'mail-in': 0, 'election-day': 0},
        'total_voted': 0, 'total_registered': 0
    }

def add_voter(demo, by, sex, party, created, voted, method=None):
    b = age_bucket(by)
    g = sex if sex in ('M', 'F') else None
    if voted:
        demo['total_voted'] += 1
        if b: demo['age'][b] += 1
        if g: demo['gender'][g] += 1
        p = (party or '').lower()
        if 'democrat' in p: demo['party']['Democratic'] += 1
        elif 'republican' in p: demo['party']['Republican'] += 1
        else: demo['party']['Other'] += 1
        # Track voting method
        m = method or 'unknown'
        if m in demo['methods']:
            demo['methods'][m] += 1
        if created:
            from datetime import datetime as _dt, timedelta as _td
            try:
                actual_date = _dt.strptime(created[:10], '%Y-%m-%d') - _td(days=1)
                d = actual_date.strftime('%Y-%m-%d')
            except:
                d = created[:10]
            demo['dates'][d] = demo['dates'].get(d, 0) + 1
            # Track method per day
            if d not in demo['method_dates']:
                demo['method_dates'][d] = {}
            demo['method_dates'][d][m] = demo['method_dates'][d].get(m, 0) + 1
    demo['total_registered'] += 1
    if b: demo['reg_age'][b] += 1
    if g: demo['reg_gender'][g] += 1

def finalize(demo):
    age = []
    for g in AGE_GROUPS:
        v, r = demo['age'][g], demo['reg_age'][g]
        age.append({'group': g, 'voted': v, 'registered': r, 'turnout_pct': round(v/r*100, 2) if r else 0})
    gender = []
    for g, label in [('F','Women'),('M','Men')]:
        v, r = demo['gender'][g], demo['reg_gender'][g]
        gender.append({'group': label, 'voted': v, 'registered': r, 'turnout_pct': round(v/r*100, 2) if r else 0})
    daily = []
    cum = 0
    for d in sorted(demo['dates'].keys()):
        cum += demo['dates'][d]
        entry = {'date': d, 'new': demo['dates'][d], 'total': cum}
        # Add method breakdown per day
        if d in demo.get('method_dates', {}):
            entry['methods'] = demo['method_dates'][d]
        daily.append(entry)
    return {'age': age, 'gender': gender, 'party': demo['party'], 'daily': daily,
            'methods': demo.get('methods', {}),
            'total_voted': demo['total_voted'], 'total_registered': demo['total_registered']}

def load_zones(path):
    zones = {}
    with open(path) as f:
        data = json.load(f)
    for feat in data['features']:
        name = feat['properties']['NAME']
        if name not in zones:
            zones[name] = feat['geometry']
        else:
            existing = zones[name]
            new = feat['geometry']
            if existing['type'] == 'Polygon' and new['type'] == 'Polygon':
                zones[name] = {'type': 'MultiPolygon', 'coordinates': [existing['coordinates'], new['coordinates']]}
            elif existing['type'] == 'MultiPolygon':
                if new['type'] == 'Polygon': existing['coordinates'].append(new['coordinates'])
                else: existing['coordinates'].extend(new['coordinates'])
    return zones

def main():
    print("Building demographics cache with zone breakdowns...")
    conn = sqlite3.connect(DB_PATH)
    ph = ','.join('?' * len(MCALLEN_ZIPS))
    
    rows = conn.execute(f"""
        SELECT v.vuid, v.lat, v.lng, v.birth_year, v.sex, v.current_party,
               ve.created_at, ve.voting_method,
               CASE WHEN ve.vuid IS NOT NULL THEN 1 ELSE 0 END as voted
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL AND v.lng IS NOT NULL
    """, (ELECTION_DATE,) + MCALLEN_ZIPS).fetchall()
    conn.close()
    print(f"Loaded {len(rows)} voters")
    
    # Load zone boundaries
    smd_zones = load_zones(SMD_PATH)
    ms_zones = load_zones(MS_PATH)
    hs_zones = load_zones(HS_PATH)
    
    # Initialize demographics
    overall = empty_demo()
    smd_demos = {n: empty_demo() for n in smd_zones}
    ms_demos = {n: empty_demo() for n in ms_zones}
    hs_demos = {n: empty_demo() for n in hs_zones}
    
    for vuid, lat, lng, by, sex, party, created, method, voted in rows:
        add_voter(overall, by, sex, party, created, voted, method)
        
        for name, geom in smd_zones.items():
            if pip_geom(lng, lat, geom):
                add_voter(smd_demos[name], by, sex, party, created, voted, method)
                break
        for name, geom in ms_zones.items():
            if pip_geom(lng, lat, geom):
                add_voter(ms_demos[name], by, sex, party, created, voted, method)
                break
        for name, geom in hs_zones.items():
            if pip_geom(lng, lat, geom):
                add_voter(hs_demos[name], by, sex, party, created, voted, method)
                break
    
    result = {
        'all': finalize(overall),
        'zones': {}
    }
    for name, demo in smd_demos.items():
        result['zones'][name] = finalize(demo)
    for name, demo in ms_demos.items():
        result['zones'][name] = finalize(demo)
    for name, demo in hs_demos.items():
        result['zones'][name] = finalize(demo)
    
    # Zone list for the dropdown
    result['zone_groups'] = {
        'City Commission': sorted(smd_zones.keys()),
        'Middle Schools': sorted(ms_zones.keys()),
        'High Schools': sorted(hs_zones.keys())
    }
    
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(result, f, separators=(',', ':'))
    
    print(f"Overall: {overall['total_voted']}/{overall['total_registered']}")
    print(f"Zones: {len(result['zones'])}")
    print(f"Cache: {Path(CACHE_PATH).stat().st_size / 1024:.0f} KB")

if __name__ == '__main__':
    main()
