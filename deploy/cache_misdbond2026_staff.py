#!/usr/bin/env python3
"""Cache MISD staff voter matching with demographic breakdowns."""
import sqlite3, json, csv
from pathlib import Path

DB = '/opt/whovoted/data/whovoted.db'
STAFF_CSV = '/opt/whovoted/data/misd_staff.csv'
CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_staff.json'
ELECTION = '2026-05-10'
MCALLEN_ZIPS = ('78501','78502','78503','78504','78505')
CURRENT_YEAR = 2026

def age_bucket(by):
    if not by or by < 1900: return 'Unknown'
    age = CURRENT_YEAR - by
    if age <= 25: return '18-25'
    if age <= 35: return '26-35'
    if age <= 45: return '36-45'
    if age <= 55: return '46-55'
    if age <= 65: return '56-65'
    return '65+'

def main():
    # Load staff names
    staff_names = []
    with open(STAFF_CSV) as f:
        reader = csv.DictReader(f)
        for row in reader:
            staff_names.append(row['name'].strip().upper())
    staff_names = list(dict.fromkeys(staff_names))  # dedupe
    print(f"Loaded {len(staff_names)} unique staff")

    conn = sqlite3.connect(DB)
    ph = ','.join('?' * len(MCALLEN_ZIPS))

    # Build voter lookup: FIRST LAST -> voter info
    all_voters = conn.execute(f"""
        SELECT v.firstname, v.lastname, v.birth_year, v.sex, v.current_party, v.vuid
        FROM voters v WHERE v.zip IN ({ph})
    """, MCALLEN_ZIPS).fetchall()

    # Build bond voter set
    bond_vuids = set(r[0] for r in conn.execute(
        "SELECT vuid FROM voter_elections WHERE election_date = ?", (ELECTION,)).fetchall())
    conn.close()

    # Index by FIRST LAST
    voter_lookup = {}
    for first, last, by, sex, party, vuid in all_voters:
        if first and last:
            key = f"{first.strip().upper()} {last.strip().upper()}"
            if key not in voter_lookup:
                voter_lookup[key] = (by, sex, party, vuid)

    # Match staff
    total = len(staff_names)
    matched = 0
    voted = 0
    not_voted = 0
    not_found = 0

    age_voted = {}; age_reg = {}
    gender_voted = {'M': 0, 'F': 0}; gender_reg = {'M': 0, 'F': 0}
    party_voted = {'Dem': 0, 'Rep': 0, 'Other': 0}
    party_reg = {'Dem': 0, 'Rep': 0, 'Other': 0}

    for name in staff_names:
        parts = name.split()
        keys_to_try = [name]
        if len(parts) >= 2:
            keys_to_try.append(f"{parts[0]} {parts[-1]}")

        found = False
        for key in keys_to_try:
            if key in voter_lookup:
                by, sex, party, vuid = voter_lookup[key]
                matched += 1
                found = True
                did_vote = vuid in bond_vuids

                bucket = age_bucket(by)
                age_reg[bucket] = age_reg.get(bucket, 0) + 1
                if sex in ('M', 'F'): gender_reg[sex] += 1
                p = (party or '').lower()
                pk = 'Dem' if 'democrat' in p else 'Rep' if 'republican' in p else 'Other'
                party_reg[pk] += 1

                if did_vote:
                    voted += 1
                    if bucket != 'Unknown': age_voted[bucket] = age_voted.get(bucket, 0) + 1
                    if sex in ('M', 'F'): gender_voted[sex] += 1
                    party_voted[pk] += 1
                else:
                    not_voted += 1
                break

        if not found:
            not_found += 1

    # Build age breakdown
    age_groups = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+']
    age_data = []
    for g in age_groups:
        v = age_voted.get(g, 0)
        r = age_reg.get(g, 0)
        age_data.append({'group': g, 'voted': v, 'registered': r,
                         'turnout_pct': round(v/r*100, 1) if r else 0})

    gender_data = []
    for g, label in [('F', 'Women'), ('M', 'Men')]:
        v = gender_voted[g]; r = gender_reg[g]
        gender_data.append({'group': label, 'voted': v, 'registered': r,
                            'turnout_pct': round(v/r*100, 1) if r else 0})

    turnout_pct = round(voted / matched * 100, 1) if matched else 0

    result = {
        'total_staff': total,
        'matched_to_voters': matched,
        'voted': voted,
        'not_voted': not_voted,
        'not_found': not_found,
        'turnout_pct': turnout_pct,
        'age': age_data,
        'gender': gender_data,
        'party': {'Democratic': party_voted['Dem'], 'Republican': party_voted['Rep'], 'Other': party_voted['Other']},
        'party_registered': {'Democratic': party_reg['Dem'], 'Republican': party_reg['Rep'], 'Other': party_reg['Other']}
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(result, f, separators=(',', ':'))

    print(f"Staff: {total}, Matched: {matched}, Voted: {voted} ({turnout_pct}%), Not voted: {not_voted}, Not found: {not_found}")
    print(f"Saved to {CACHE_PATH}")

if __name__ == '__main__':
    main()
