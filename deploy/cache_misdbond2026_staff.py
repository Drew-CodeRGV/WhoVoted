#!/usr/bin/env python3
"""Cache MISD staff voter matching with role + demographic breakdowns.
Uses misd_staff_v2.csv (with title/department/role) if available,
falls back to misd_staff.csv (name only)."""
import sqlite3, json, csv, os
from pathlib import Path

DB = '/opt/whovoted/data/whovoted.db'
STAFF_V2 = '/opt/whovoted/data/misd_staff_v2.csv'
STAFF_V1 = '/opt/whovoted/data/misd_staff.csv'
CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_staff.json'
ELECTION = '2026-05-10'
MCALLEN_ZIPS = ('78501','78502','78503','78504','78505')
YEAR = 2026

ROLE_ICONS = {'Instructional':'📚','Admin & Support':'🏢',
              'Facilities & Operations':'🔧','Substitute':'🔄','Other':'❓'}
ROLE_ORDER = ['Instructional','Admin & Support','Facilities & Operations','Substitute','Other']

def age_bucket(by):
    if not by or by < 1900: return 'Unknown'
    a = YEAR - by
    if a <= 25: return '18-25'
    if a <= 35: return '26-35'
    if a <= 45: return '36-45'
    if a <= 55: return '46-55'
    if a <= 65: return '56-65'
    return '65+'

def load_staff():
    """Load staff list, preferring v2 (with roles) over v1 (names only)."""
    if os.path.exists(STAFF_V2) and os.path.getsize(STAFF_V2) > 0:
        print(f"Using v2 staff file: {STAFF_V2}")
        staff = []
        with open(STAFF_V2) as f:
            for row in csv.DictReader(f):
                staff.append({'name': row['name'].strip().upper(),
                              'role': row.get('role', 'Other')})
        return staff, True
    elif os.path.exists(STAFF_V1):
        print(f"Using v1 staff file (no roles): {STAFF_V1}")
        staff = []
        with open(STAFF_V1) as f:
            for row in csv.DictReader(f):
                staff.append({'name': row['name'].strip().upper(), 'role': 'Other'})
        return staff, False
    else:
        print("No staff CSV found. Run scrape_misd_staff_v2.py first.")
        return [], False

def main():
    staff_list, has_roles = load_staff()
    # Dedupe by name
    seen = {}
    for s in staff_list:
        if s['name'] not in seen:
            seen[s['name']] = s
    staff = list(seen.values())
    print(f"Loaded {len(staff)} unique staff")

    conn = sqlite3.connect(DB)
    ph = ','.join('?' * len(MCALLEN_ZIPS))
    all_voters = conn.execute(f"SELECT firstname,lastname,birth_year,sex,current_party,vuid FROM voters WHERE zip IN ({ph})", MCALLEN_ZIPS).fetchall()
    bond_vuids = set(r[0] for r in conn.execute("SELECT vuid FROM voter_elections WHERE election_date=?", (ELECTION,)))
    conn.close()

    vlookup = {}
    for first, last, by, sex, party, vuid in all_voters:
        if first and last:
            k = f"{first.strip().upper()} {last.strip().upper()}"
            if k not in vlookup:
                vlookup[k] = (by, sex, party, vuid)

    # Accumulators
    roles = {r: {'total':0,'matched':0,'voted':0} for r in ROLE_ORDER}
    age_v = {}; age_r = {}
    gen_v = {'M':0,'F':0}; gen_r = {'M':0,'F':0}
    par_v = {'Dem':0,'Rep':0,'Other':0}; par_r = {'Dem':0,'Rep':0,'Other':0}
    total_matched = 0; total_voted = 0; total_nf = 0

    for s in staff:
        role = s['role'] if s['role'] in roles else 'Other'
        roles[role]['total'] += 1
        name = s['name']; parts = name.split()
        keys = [name]
        if len(parts) >= 2: keys.append(f"{parts[0]} {parts[-1]}")

        hit = False
        for k in keys:
            if k in vlookup:
                by, sex, party, vuid = vlookup[k]
                hit = True; total_matched += 1; roles[role]['matched'] += 1
                did = vuid in bond_vuids
                b = age_bucket(by)
                age_r[b] = age_r.get(b,0)+1
                if sex in ('M','F'): gen_r[sex] += 1
                p = (party or '').lower()
                pk = 'Dem' if 'democrat' in p else 'Rep' if 'republican' in p else 'Other'
                par_r[pk] += 1
                if did:
                    total_voted += 1; roles[role]['voted'] += 1
                    age_v[b] = age_v.get(b,0)+1
                    if sex in ('M','F'): gen_v[sex] += 1
                    par_v[pk] += 1
                break
        if not hit: total_nf += 1

    # Build output
    role_data = []
    for r in ROLE_ORDER:
        d = roles[r]
        if d['total'] > 0:
            pct = round(d['voted']/d['matched']*100,1) if d['matched'] else 0
            role_data.append({'role':r,'icon':ROLE_ICONS.get(r,''),'total':d['total'],
                              'matched':d['matched'],'voted':d['voted'],
                              'not_voted':d['matched']-d['voted'],'turnout_pct':pct})

    ags = ['18-25','26-35','36-45','46-55','56-65','65+']
    age_data = [{'group':g,'voted':age_v.get(g,0),'registered':age_r.get(g,0),
                 'turnout_pct':round(age_v.get(g,0)/age_r[g]*100,1) if age_r.get(g,0) else 0} for g in ags]
    gen_data = [{'group':l,'voted':gen_v[g],'registered':gen_r[g],
                 'turnout_pct':round(gen_v[g]/gen_r[g]*100,1) if gen_r[g] else 0} for g,l in [('F','Women'),('M','Men')]]
    tp = round(total_voted/total_matched*100,1) if total_matched else 0

    result = {
        'total_staff': len(staff), 'matched_to_voters': total_matched,
        'voted': total_voted, 'not_voted': total_matched - total_voted,
        'not_found': total_nf, 'turnout_pct': tp,
        'roles': role_data, 'age': age_data, 'gender': gen_data,
        'party': {'Democratic':par_v['Dem'],'Republican':par_v['Rep'],'Other':par_v['Other']},
        'party_registered': {'Democratic':par_r['Dem'],'Republican':par_r['Rep'],'Other':par_r['Other']}
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH,'w') as f:
        json.dump(result, f, separators=(',',':'))

    print(f"Staff: {len(staff)}, Matched: {total_matched}, Voted: {total_voted} ({tp}%)")
    if role_data:
        for r in role_data:
            print(f"  {r['icon']} {r['role']}: {r['total']} staff, {r['voted']}/{r['matched']} voted ({r['turnout_pct']}%)")
    print(f"Saved to {CACHE_PATH}")

if __name__ == '__main__':
    main()
