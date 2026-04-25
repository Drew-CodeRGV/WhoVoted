#!/usr/bin/env python3
"""Cross-tabulated demographic analysis of McAllen ISD Bond 2026 voters."""
import sqlite3

DB = '/opt/whovoted/data/whovoted.db'
ZIPS = ('78501','78502','78503','78504','78505')
ELECTION = '2026-05-10'

conn = sqlite3.connect(DB)
ph = ','.join('?' * len(ZIPS))

# Get all voters with voted flag
rows = conn.execute(f"""
    SELECT
        CASE
            WHEN (2026 - v.birth_year) BETWEEN 18 AND 25 THEN '18-25'
            WHEN (2026 - v.birth_year) BETWEEN 26 AND 35 THEN '26-35'
            WHEN (2026 - v.birth_year) BETWEEN 36 AND 45 THEN '36-45'
            WHEN (2026 - v.birth_year) BETWEEN 46 AND 55 THEN '46-55'
            WHEN (2026 - v.birth_year) BETWEEN 56 AND 65 THEN '56-65'
            WHEN (2026 - v.birth_year) > 65 THEN '65+'
            ELSE 'Unknown'
        END as age_group,
        COALESCE(v.sex, 'U') as gender,
        CASE
            WHEN LOWER(COALESCE(v.current_party,'')) LIKE '%democrat%' THEN 'Dem'
            WHEN LOWER(COALESCE(v.current_party,'')) LIKE '%republican%' THEN 'Rep'
            ELSE 'Other'
        END as party,
        CASE WHEN ve.vuid IS NOT NULL THEN 1 ELSE 0 END as voted
    FROM voters v
    LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
    WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL AND v.lng IS NOT NULL
""", (ELECTION,) + ZIPS).fetchall()
conn.close()

# Build cross-tab
from collections import defaultdict
data = defaultdict(lambda: {'voted': 0, 'reg': 0})
for age, gender, party, voted in rows:
    key = (age, gender, party)
    data[key]['reg'] += 1
    if voted:
        data[key]['voted'] += 1

AGE_ORDER = ['18-25', '26-35', '36-45', '46-55', '56-65', '65+']

print("=" * 80)
print("McAllen ISD Bond 2026 - WHO IS ACTUALLY VOTING?")
print("=" * 80)

# 1. Age x Party (both genders)
print("\n--- TURNOUT BY AGE + PARTY ---")
print(f"{'Age':<8} {'Dem Voted':>10} {'Dem Reg':>10} {'Dem %':>7} | {'Rep Voted':>10} {'Rep Reg':>10} {'Rep %':>7} | {'Other V':>8} {'Other R':>8} {'Oth %':>7}")
for age in AGE_ORDER:
    d = data[(age, 'F', 'Dem')]; d2 = data[(age, 'M', 'Dem')]
    dv = d['voted'] + d2['voted']; dr = d['reg'] + d2['reg']
    r = data[(age, 'F', 'Rep')]; r2 = data[(age, 'M', 'Rep')]
    rv = r['voted'] + r2['voted']; rr = r['reg'] + r2['reg']
    o = data[(age, 'F', 'Other')]; o2 = data[(age, 'M', 'Other')]
    ov = o['voted'] + o2['voted']; orr = o['reg'] + o2['reg']
    dp = f"{dv/dr*100:.1f}%" if dr else "0%"
    rp = f"{rv/rr*100:.1f}%" if rr else "0%"
    op = f"{ov/orr*100:.1f}%" if orr else "0%"
    print(f"{age:<8} {dv:>10,} {dr:>10,} {dp:>7} | {rv:>10,} {rr:>10,} {rp:>7} | {ov:>8,} {orr:>8,} {op:>7}")

# 2. Gender x Party
print("\n--- TURNOUT BY GENDER + PARTY ---")
print(f"{'Gender':<8} {'Dem Voted':>10} {'Dem Reg':>10} {'Dem %':>7} | {'Rep Voted':>10} {'Rep Reg':>10} {'Rep %':>7}")
for g, label in [('F', 'Women'), ('M', 'Men')]:
    dv = sum(data[(a, g, 'Dem')]['voted'] for a in AGE_ORDER)
    dr = sum(data[(a, g, 'Dem')]['reg'] for a in AGE_ORDER)
    rv = sum(data[(a, g, 'Rep')]['voted'] for a in AGE_ORDER)
    rr = sum(data[(a, g, 'Rep')]['reg'] for a in AGE_ORDER)
    dp = f"{dv/dr*100:.1f}%" if dr else "0%"
    rp = f"{rv/rr*100:.1f}%" if rr else "0%"
    print(f"{label:<8} {dv:>10,} {dr:>10,} {dp:>7} | {rv:>10,} {rr:>10,} {rp:>7}")

# 3. The full cross-tab: Age x Gender x Party
print("\n--- FULL CROSS-TAB: Age x Gender x Party (Voted / Registered = Turnout%) ---")
print(f"{'Age':<7} {'Gender':<7} {'Dem V':>6} {'Dem R':>7} {'D%':>6} | {'Rep V':>6} {'Rep R':>7} {'R%':>6} | {'Oth V':>6} {'Oth R':>7} {'O%':>6}")
for age in AGE_ORDER:
    for g, gl in [('F', 'Women'), ('M', 'Men')]:
        d = data[(age, g, 'Dem')]
        r = data[(age, g, 'Rep')]
        o = data[(age, g, 'Other')]
        dp = f"{d['voted']/d['reg']*100:.1f}%" if d['reg'] else "-"
        rp = f"{r['voted']/r['reg']*100:.1f}%" if r['reg'] else "-"
        op = f"{o['voted']/o['reg']*100:.1f}%" if o['reg'] else "-"
        print(f"{age:<7} {gl:<7} {d['voted']:>6,} {d['reg']:>7,} {dp:>6} | {r['voted']:>6,} {r['reg']:>7,} {rp:>6} | {o['voted']:>6,} {o['reg']:>7,} {op:>6}")

# 4. Top stories
print("\n" + "=" * 80)
print("KEY FINDINGS")
print("=" * 80)

# Find highest turnout cell
best = max(data.items(), key=lambda x: (x[1]['voted']/x[1]['reg']*100) if x[1]['reg'] > 50 else 0)
bp = best[1]['voted']/best[1]['reg']*100 if best[1]['reg'] else 0
gl = 'Women' if best[0][1] == 'F' else 'Men'
print(f"\nHighest turnout group: {best[0][0]} {gl} ({best[0][2]}) at {bp:.1f}% ({best[1]['voted']}/{best[1]['reg']})")

# Find lowest turnout cell (min 50 registered)
worst = min((x for x in data.items() if x[1]['reg'] > 50), key=lambda x: x[1]['voted']/x[1]['reg']*100)
wp = worst[1]['voted']/worst[1]['reg']*100 if worst[1]['reg'] else 0
gl2 = 'Women' if worst[0][1] == 'F' else 'Men'
print(f"Lowest turnout group:  {worst[0][0]} {gl2} ({worst[0][2]}) at {wp:.1f}% ({worst[1]['voted']}/{worst[1]['reg']})")

# Total Dem vs Rep
total_dem_v = sum(v['voted'] for k, v in data.items() if k[2] == 'Dem')
total_dem_r = sum(v['reg'] for k, v in data.items() if k[2] == 'Dem')
total_rep_v = sum(v['voted'] for k, v in data.items() if k[2] == 'Rep')
total_rep_r = sum(v['reg'] for k, v in data.items() if k[2] == 'Rep')
print(f"\nDemocrats: {total_dem_v:,} voted of {total_dem_r:,} registered ({total_dem_v/total_dem_r*100:.1f}%)")
print(f"Republicans: {total_rep_v:,} voted of {total_rep_r:,} registered ({total_rep_v/total_rep_r*100:.1f}%)")

# Women vs Men overall
total_f_v = sum(v['voted'] for k, v in data.items() if k[1] == 'F')
total_f_r = sum(v['reg'] for k, v in data.items() if k[1] == 'F')
total_m_v = sum(v['voted'] for k, v in data.items() if k[1] == 'M')
total_m_r = sum(v['reg'] for k, v in data.items() if k[1] == 'M')
print(f"\nWomen: {total_f_v:,} voted of {total_f_r:,} ({total_f_v/total_f_r*100:.1f}%)")
print(f"Men:   {total_m_v:,} voted of {total_m_r:,} ({total_m_v/total_m_r*100:.1f}%)")

# Dem women vs Rep women
dem_f_v = sum(v['voted'] for k, v in data.items() if k[1] == 'F' and k[2] == 'Dem')
dem_f_r = sum(v['reg'] for k, v in data.items() if k[1] == 'F' and k[2] == 'Dem')
rep_f_v = sum(v['voted'] for k, v in data.items() if k[1] == 'F' and k[2] == 'Rep')
rep_f_r = sum(v['reg'] for k, v in data.items() if k[1] == 'F' and k[2] == 'Rep')
print(f"\nDem Women: {dem_f_v:,} voted of {dem_f_r:,} ({dem_f_v/dem_f_r*100:.1f}%)")
print(f"Rep Women: {rep_f_v:,} voted of {rep_f_r:,} ({rep_f_v/rep_f_r*100:.1f}%)")

# Old Dems vs Young Dems
old_dem_v = sum(v['voted'] for k, v in data.items() if k[2] == 'Dem' and k[0] in ('56-65', '65+'))
old_dem_r = sum(v['reg'] for k, v in data.items() if k[2] == 'Dem' and k[0] in ('56-65', '65+'))
young_dem_v = sum(v['voted'] for k, v in data.items() if k[2] == 'Dem' and k[0] in ('18-25', '26-35'))
young_dem_r = sum(v['reg'] for k, v in data.items() if k[2] == 'Dem' and k[0] in ('18-25', '26-35'))
print(f"\nOld Democrats (56+): {old_dem_v:,} voted of {old_dem_r:,} ({old_dem_v/old_dem_r*100:.1f}%)")
print(f"Young Democrats (18-35): {young_dem_v:,} voted of {young_dem_r:,} ({young_dem_v/young_dem_r*100:.1f}%)")

old_rep_v = sum(v['voted'] for k, v in data.items() if k[2] == 'Rep' and k[0] in ('56-65', '65+'))
old_rep_r = sum(v['reg'] for k, v in data.items() if k[2] == 'Rep' and k[0] in ('56-65', '65+'))
young_rep_v = sum(v['voted'] for k, v in data.items() if k[2] == 'Rep' and k[0] in ('18-25', '26-35'))
young_rep_r = sum(v['reg'] for k, v in data.items() if k[2] == 'Rep' and k[0] in ('18-25', '26-35'))
print(f"Old Republicans (56+): {old_rep_v:,} voted of {old_rep_r:,} ({old_rep_v/old_rep_r*100:.1f}%)")
print(f"Young Republicans (18-35): {young_rep_v:,} voted of {young_rep_r:,} ({young_rep_v/young_rep_r*100:.1f}%)")
