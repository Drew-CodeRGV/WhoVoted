#!/usr/bin/env python3
"""Scrape McAllen ISD staff directory with titles and departments, then match against bond voters."""
import requests, re, sqlite3, csv, json, time
from pathlib import Path

BASE = 'https://www.mcallenisd.org/staff'
DB = '/opt/whovoted/data/whovoted.db'
ELECTION = '2026-05-10'
MCALLEN_ZIPS = ('78501','78502','78503','78504','78505')
STAFF_CSV = '/opt/whovoted/data/misd_staff_v2.csv'
CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_staff.json'
CURRENT_YEAR = 2026

# Role classification
INSTRUCTIONAL_KEYWORDS = [
    'TEACHER', 'TCHR', 'PRINCIPAL', 'ASST PRINCIPAL', 'AP ', 'COUNSELOR',
    'LIBRARIAN', 'COACH', 'COORD', 'SPECIALIST', 'SPEC ', 'DIR ',
    'INSTRUCTOR', 'TUTOR', 'INTERVENTIONIST', 'DIAGNOSTICIAN',
    'BILINGUAL', 'ESL', 'SPED', 'SPECIAL ED', 'CURRICULUM',
    'INSTRUCTIONAL', 'ASSESSMENT', 'READING', 'MATH', 'SCIENCE',
    'ENGLISH', 'SOCIAL STUDIES', 'FINE ARTS', 'MUSIC', 'ART ',
    'PE ', 'PHYSICAL ED', 'NURSE', 'SPEECH', 'THERAPIST', 'PSYCHOLOGIST'
]
FACILITIES_KEYWORDS = [
    'CUSTODIAN', 'JANITOR', 'MAINTENANCE', 'MAINT', 'CARPENTER',
    'ELECTRICIAN', 'PLUMBER', 'HVAC', 'GROUNDSKEEPER', 'GROUNDS',
    'FACILITIES', 'BUS DRIVER', 'TRANSPORTATION', 'MECHANIC',
    'WAREHOUSE', 'DELIVERY', 'FOOD SERVICE', 'CAFETERIA', 'CHILD NUTRITION',
    'POLICE', 'OFFICER', 'SECURITY', 'GUARD'
]
SUBSTITUTE_KEYWORDS = ['SUBSTITUTE', 'SUB ']
SUPPORT_KEYWORDS = [
    'CLERK', 'SECRETARY', 'RECEPTIONIST', 'REGISTRAR', 'AIDE',
    'PARA', 'PARAPROFESSIONAL', 'ATTENDANCE', 'DATA ENTRY',
    'PAYROLL', 'ACCOUNTING', 'BUDGET', 'FINANCE', 'HUMAN RESOURCES',
    'PURCHASING', 'TECHNOLOGY', 'TECH ', 'IT ', 'NETWORK',
    'ADMIN', 'EXECUTIVE', 'SUPERINTENDENT', 'COMMUNICATIONS'
]

def classify_role(title, dept):
    """Classify a staff member into a role category."""
    combined = (title + ' ' + dept).upper()
    if any(k in combined for k in SUBSTITUTE_KEYWORDS):
        return 'Substitute'
    if any(k in combined for k in INSTRUCTIONAL_KEYWORDS):
        return 'Instructional'
    if any(k in combined for k in FACILITIES_KEYWORDS):
        return 'Facilities & Operations'
    if any(k in combined for k in SUPPORT_KEYWORDS):
        return 'Admin & Support'
    return 'Other'

def scrape_all_staff():
    """Scrape all pages, extracting name + title + department."""
    all_staff = []
    seen = set()
    
    for page in range(1, 100):
        url = f'{BASE}?page_no={page}'
        print(f"  Page {page}...", end=' ')
        try:
            resp = requests.get(url, timeout=15)
            resp.raise_for_status()
            html = resp.text
        except Exception as e:
            print(f"Error: {e}")
            break
        
        # Extract staff using the actual HTML structure:
        # <div class="name" ...>NAME</div>
        # <div class="title" ...>TITLE</div>
        # <div class="department" ...>DEPARTMENT</div>
        entries = re.findall(
            r'<div class="name"[^>]*>([^<]+)</div>\s*'
            r'<div class="title"[^>]*>([^<]+)</div>\s*'
            r'<div class="department"[^>]*>([^<]+)</div>',
            html
        )
        
        if not entries:
            print("No entries found, stopping.")
            break
        
        count = 0
        for name, title, dept in entries:
            name = name.strip().upper()
            if name and name not in seen:
                seen.add(name)
                role = classify_role(title.strip(), dept.strip())
                all_staff.append({
                    'name': name,
                    'title': title.strip().upper(),
                    'department': dept.strip().upper(),
                    'role': role
                })
                count += 1
        
        print(f"{count} new (total: {len(all_staff)})")
        
        if f'page_no={page + 1}' not in html:
            print("  Last page.")
            break
        time.sleep(0.3)
    
    return all_staff

def age_bucket(by):
    if not by or by < 1900: return 'Unknown'
    age = CURRENT_YEAR - by
    if age <= 25: return '18-25'
    if age <= 35: return '26-35'
    if age <= 45: return '36-45'
    if age <= 55: return '46-55'
    if age <= 65: return '56-65'
    return '65+'

def build_cache(staff_list):
    """Match staff against voter DB and build cache with role breakdowns."""
    conn = sqlite3.connect(DB)
    ph = ','.join('?' * len(MCALLEN_ZIPS))

    all_voters = conn.execute(f"""
        SELECT v.firstname, v.lastname, v.birth_year, v.sex, v.current_party, v.vuid
        FROM voters v WHERE v.zip IN ({ph})
    """, MCALLEN_ZIPS).fetchall()
    bond_vuids = set(r[0] for r in conn.execute(
        "SELECT vuid FROM voter_elections WHERE election_date = ?", (ELECTION,)).fetchall())
    conn.close()

    voter_lookup = {}
    for first, last, by, sex, party, vuid in all_voters:
        if first and last:
            key = f"{first.strip().upper()} {last.strip().upper()}"
            if key not in voter_lookup:
                voter_lookup[key] = (by, sex, party, vuid)

    # Dedupe staff by name
    unique = {}
    for s in staff_list:
        if s['name'] not in unique:
            unique[s['name']] = s
    staff = list(unique.values())

    # Aggregate by role
    roles = {}
    age_voted = {}; age_reg = {}
    gender_voted = {'M': 0, 'F': 0}; gender_reg = {'M': 0, 'F': 0}
    party_voted = {'Dem': 0, 'Rep': 0, 'Other': 0}
    party_reg = {'Dem': 0, 'Rep': 0, 'Other': 0}
    total_matched = 0; total_voted = 0; total_not_found = 0

    for s in staff:
        role = s['role']
        if role not in roles:
            roles[role] = {'total': 0, 'matched': 0, 'voted': 0}
        roles[role]['total'] += 1

        # Try to match
        name = s['name']
        parts = name.split()
        keys = [name]
        if len(parts) >= 2:
            keys.append(f"{parts[0]} {parts[-1]}")

        matched = False
        for key in keys:
            if key in voter_lookup:
                by, sex, party, vuid = voter_lookup[key]
                matched = True
                total_matched += 1
                roles[role]['matched'] += 1
                did_vote = vuid in bond_vuids

                bucket = age_bucket(by)
                age_reg[bucket] = age_reg.get(bucket, 0) + 1
                if sex in ('M', 'F'): gender_reg[sex] += 1
                p = (party or '').lower()
                pk = 'Dem' if 'democrat' in p else 'Rep' if 'republican' in p else 'Other'
                party_reg[pk] += 1

                if did_vote:
                    total_voted += 1
                    roles[role]['voted'] += 1
                    age_voted[bucket] = age_voted.get(bucket, 0) + 1
                    if sex in ('M', 'F'): gender_voted[sex] += 1
                    party_voted[pk] += 1
                break

        if not matched:
            total_not_found += 1

    # Build role breakdown for display
    role_order = ['Instructional', 'Admin & Support', 'Facilities & Operations', 'Substitute', 'Other']
    role_icons = {'Instructional': '📚', 'Admin & Support': '🏢', 'Facilities & Operations': '🔧', 'Substitute': '🔄', 'Other': '❓'}
    role_data = []
    for r in role_order:
        if r in roles:
            d = roles[r]
            pct = round(d['voted'] / d['matched'] * 100, 1) if d['matched'] else 0
            role_data.append({
                'role': r, 'icon': role_icons.get(r, ''),
                'total': d['total'], 'matched': d['matched'], 'voted': d['voted'],
                'not_voted': d['matched'] - d['voted'],
                'turnout_pct': pct
            })

    age_groups = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+']
    age_data = [{'group': g, 'voted': age_voted.get(g, 0), 'registered': age_reg.get(g, 0),
                 'turnout_pct': round(age_voted.get(g, 0) / age_reg.get(g, 1) * 100, 1) if age_reg.get(g, 0) else 0}
                for g in age_groups]

    gender_data = [{'group': l, 'voted': gender_voted[g], 'registered': gender_reg[g],
                    'turnout_pct': round(gender_voted[g] / gender_reg[g] * 100, 1) if gender_reg[g] else 0}
                   for g, l in [('F', 'Women'), ('M', 'Men')]]

    turnout_pct = round(total_voted / total_matched * 100, 1) if total_matched else 0

    result = {
        'total_staff': len(staff),
        'matched_to_voters': total_matched,
        'voted': total_voted,
        'not_voted': total_matched - total_voted,
        'not_found': total_not_found,
        'turnout_pct': turnout_pct,
        'roles': role_data,
        'age': age_data,
        'gender': gender_data,
        'party': {'Democratic': party_voted['Dem'], 'Republican': party_voted['Rep'], 'Other': party_voted['Other']},
        'party_registered': {'Democratic': party_reg['Dem'], 'Republican': party_reg['Rep'], 'Other': party_reg['Other']}
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(result, f, separators=(',', ':'))

    print(f"\nStaff: {len(staff)}, Matched: {total_matched}, Voted: {total_voted} ({turnout_pct}%)")
    print(f"Roles:")
    for r in role_data:
        print(f"  {r['icon']} {r['role']}: {r['total']} staff, {r['matched']} in rolls, {r['voted']} voted ({r['turnout_pct']}%)")

def main():
    print("=== Scraping McAllen ISD Staff Directory v2 ===")
    staff = scrape_all_staff()
    print(f"\nTotal: {len(staff)}")

    # Save CSV
    with open(STAFF_CSV, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=['name', 'title', 'department', 'role'])
        w.writeheader()
        w.writerows(staff)
    print(f"Saved to {STAFF_CSV}")

    print("\n=== Building Cache ===")
    build_cache(staff)

if __name__ == '__main__':
    main()
