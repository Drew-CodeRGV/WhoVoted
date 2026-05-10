#!/usr/bin/env python3
"""Cache demographic breakdown for HD-41 voters."""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_demographics.json'
# HD-41 runoff — May 26, 2026
ELECTION_DATE = '2026-05-26'
DISTRICT = 'HD-41'
CURRENT_YEAR = 2026

AGE_GROUPS = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+']

def age_bucket(by):
    if not by or by < 1900:
        return None
    age = CURRENT_YEAR - by
    if age < 18: return None
    if age <= 25: return '18-25'
    if age <= 35: return '26-35'
    if age <= 45: return '36-45'
    if age <= 55: return '46-55'
    if age <= 65: return '56-65'
    return '65+'

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
        m = method or 'unknown'
        if m in demo['methods']:
            demo['methods'][m] += 1
        if created:
            d = created[:10]
            demo['dates'][d] = demo['dates'].get(d, 0) + 1
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
    for g, label in [('F', 'Women'), ('M', 'Men')]:
        v, r = demo['gender'][g], demo['reg_gender'][g]
        gender.append({'group': label, 'voted': v, 'registered': r, 'turnout_pct': round(v/r*100, 2) if r else 0})
    daily = []
    cum = 0
    for d in sorted(demo['dates'].keys()):
        cum += demo['dates'][d]
        entry = {'date': d, 'new': demo['dates'][d], 'total': cum}
        if d in demo.get('method_dates', {}):
            entry['methods'] = demo['method_dates'][d]
        daily.append(entry)
    return {'age': age, 'gender': gender, 'party': demo['party'], 'daily': daily,
            'methods': demo.get('methods', {}),
            'total_voted': demo['total_voted'], 'total_registered': demo['total_registered']}

def main():
    print(f"Building demographics cache for {DISTRICT}...")
    conn = sqlite3.connect(DB_PATH)

    rows = conn.execute("""
        SELECT v.vuid, v.lat, v.lng, v.birth_year, v.sex, v.current_party,
               ve.created_at, ve.voting_method,
               CASE WHEN ve.vuid IS NOT NULL THEN 1 ELSE 0 END as voted
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.state_house_district = ?
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
    """, (ELECTION_DATE, DISTRICT)).fetchall()
    conn.close()
    print(f"Loaded {len(rows)} voters")

    # Build overall demographics (no zone breakdowns for HD-41 — use precinct-level instead)
    overall = empty_demo()
    precinct_demos = {}

    for vuid, lat, lng, by, sex, party, created, method, voted in rows:
        add_voter(overall, by, sex, party, created, voted, method)

    result = {
        'all': finalize(overall),
        'zones': {},
        'zone_groups': {}
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(result, f, separators=(',', ':'))

    print(f"Overall: {overall['total_voted']}/{overall['total_registered']}")
    print(f"Cache: {Path(CACHE_PATH).stat().st_size / 1024:.0f} KB")

if __name__ == '__main__':
    main()
