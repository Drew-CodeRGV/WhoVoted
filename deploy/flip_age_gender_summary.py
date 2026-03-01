#!/usr/bin/env python3
"""Summary of flipped voters by age group and gender for 2026 primary."""
import sqlite3

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')

# First check birth_year coverage
total_voters = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
has_birth_year = conn.execute("SELECT COUNT(*) FROM voters WHERE birth_year IS NOT NULL AND birth_year > 0").fetchone()[0]
print(f"=== Birth Year Coverage ===")
print(f"Total voters: {total_voters:,}")
print(f"With birth_year: {has_birth_year:,} ({has_birth_year/total_voters*100:.1f}%)")
print()

# Sample birth years
rows = conn.execute("SELECT birth_year, COUNT(*) FROM voters WHERE birth_year IS NOT NULL AND birth_year > 0 GROUP BY birth_year ORDER BY birth_year LIMIT 10").fetchall()
print("Sample birth years (oldest):", rows)
rows2 = conn.execute("SELECT birth_year, COUNT(*) FROM voters WHERE birth_year IS NOT NULL AND birth_year > 0 GROUP BY birth_year ORDER BY birth_year DESC LIMIT 10").fetchall()
print("Sample birth years (youngest):", rows2)
print()

# Get all flipped voters in 2026 with age and gender
print("=== 2026 Flipped Voters by Age Group and Gender ===")
flips = conn.execute("""
    SELECT 
        ve_current.party_voted as to_party,
        ve_prev.party_voted as from_party,
        v.birth_year,
        v.sex,
        COUNT(*) as cnt
    FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    JOIN voters v ON ve_current.vuid = v.vuid
    WHERE ve_current.election_date = '2026-03-03'
        AND ve_prev.election_date = (
            SELECT MAX(ve2.election_date) FROM voter_elections ve2
            WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
        AND ve_current.party_voted != ve_prev.party_voted
        AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
    GROUP BY ve_current.party_voted, ve_prev.party_voted, v.birth_year, v.sex
""").fetchall()

# Organize into age groups
from collections import defaultdict
current_year = 2026

age_groups = {
    '18-24': (2002, 2008),
    '25-34': (1992, 2001),
    '35-44': (1982, 1991),
    '45-54': (1972, 1981),
    '55-64': (1962, 1971),
    '65-74': (1952, 1961),
    '75+': (0, 1951),
}

def get_age_group(birth_year):
    if not birth_year or birth_year <= 0:
        return 'Unknown'
    for group, (lo, hi) in age_groups.items():
        if lo <= birth_year <= hi:
            return group
    return 'Unknown'

# R→D flips
r2d_data = defaultdict(lambda: defaultdict(int))
d2r_data = defaultdict(lambda: defaultdict(int))

for to_p, from_p, by, sex, cnt in flips:
    ag = get_age_group(by)
    gender = 'F' if sex == 'F' else 'M' if sex == 'M' else 'U'
    if from_p == 'Republican' and to_p == 'Democratic':
        r2d_data[ag][gender] += cnt
    elif from_p == 'Democratic' and to_p == 'Republican':
        d2r_data[ag][gender] += cnt

print("\n--- R→D Flips (Republican to Democrat) ---")
print(f"{'Age Group':<12} {'Female':>8} {'Male':>8} {'Unknown':>8} {'Total':>8}")
print("-" * 48)
total_r2d = {'F': 0, 'M': 0, 'U': 0}
for ag in list(age_groups.keys()) + ['Unknown']:
    f = r2d_data[ag]['F']
    m = r2d_data[ag]['M']
    u = r2d_data[ag]['U']
    total_r2d['F'] += f
    total_r2d['M'] += m
    total_r2d['U'] += u
    print(f"{ag:<12} {f:>8,} {m:>8,} {u:>8,} {f+m+u:>8,}")
print("-" * 48)
print(f"{'TOTAL':<12} {total_r2d['F']:>8,} {total_r2d['M']:>8,} {total_r2d['U']:>8,} {sum(total_r2d.values()):>8,}")

print("\n--- D→R Flips (Democrat to Republican) ---")
print(f"{'Age Group':<12} {'Female':>8} {'Male':>8} {'Unknown':>8} {'Total':>8}")
print("-" * 48)
total_d2r = {'F': 0, 'M': 0, 'U': 0}
for ag in list(age_groups.keys()) + ['Unknown']:
    f = d2r_data[ag]['F']
    m = d2r_data[ag]['M']
    u = d2r_data[ag]['U']
    total_d2r['F'] += f
    total_d2r['M'] += m
    total_d2r['U'] += u
    print(f"{ag:<12} {f:>8,} {m:>8,} {u:>8,} {f+m+u:>8,}")
print("-" * 48)
print(f"{'TOTAL':<12} {total_d2r['F']:>8,} {total_d2r['M']:>8,} {total_d2r['U']:>8,} {sum(total_d2r.values()):>8,}")

print("\n--- Net Flip by Age Group (R→D minus D→R) ---")
print(f"{'Age Group':<12} {'Net':>8} {'Direction':>12}")
print("-" * 36)
for ag in list(age_groups.keys()) + ['Unknown']:
    r2d_total = sum(r2d_data[ag].values())
    d2r_total = sum(d2r_data[ag].values())
    net = r2d_total - d2r_total
    direction = '→ DEM' if net > 0 else '→ REP' if net < 0 else 'EVEN'
    print(f"{ag:<12} {net:>+8,} {direction:>12}")

conn.close()
