#!/usr/bin/env python3
"""Build the south McAllen story: lowest turnout + highest student need + bond impact."""
import sqlite3, json

DB = '/opt/whovoted/data/whovoted.db'
ZIPS = ('78501','78502','78503','78504','78505')
ELECTION = '2026-05-10'

conn = sqlite3.connect(DB)
ph = ','.join('?' * len(ZIPS))

# 1. Load all report card data
print("=== ELEMENTARY SCHOOLS (worst first) ===")
with open('/opt/whovoted/public/cache/misdbond2026_elem_reportcard.json') as f:
    elem = json.load(f)
for c in sorted(elem['campuses'], key=lambda x: x['turnout_pct']):
    print(f"  {c['name']:<25s} {c['voted']:>4}/{c['registered']:>6} = {c['turnout_pct']:.2f}% ({c['grade']})")

print("\n=== MIDDLE SCHOOLS (worst first) ===")
with open('/opt/whovoted/public/cache/misdbond2026_campus_reportcard.json') as f:
    ms = json.load(f)
for c in sorted(ms['campuses'], key=lambda x: x['turnout_pct']):
    print(f"  {c['name']:<25s} {c['voted']:>4}/{c['registered']:>6} = {c['turnout_pct']:.2f}% ({c['grade']})")

print("\n=== HIGH SCHOOLS (worst first) ===")
with open('/opt/whovoted/public/cache/misdbond2026_hs_reportcard.json') as f:
    hs = json.load(f)
for c in sorted(hs['campuses'], key=lambda x: x['turnout_pct']):
    print(f"  {c['name']:<25s} {c['voted']:>4}/{c['registered']:>6} = {c['turnout_pct']:.2f}% ({c['grade']})")

print("\n=== CITY COMMISSION DISTRICTS (worst first) ===")
with open('/opt/whovoted/public/cache/misdbond2026_reportcard.json') as f:
    dist = json.load(f)
for d in sorted(dist['districts'], key=lambda x: x['turnout_pct']):
    print(f"  District {d['district']} ({d['rep']:<30s}) {d['voted']:>4}/{d['registered']:>6} = {d['turnout_pct']:.2f}% ({d['grade']})")

# 2. Student population estimates from cache
print("\n=== STUDENT POPULATION DATA ===")
try:
    with open('/opt/whovoted/public/cache/misdbond2026_students.json') as f:
        stu = json.load(f)
    elem_count = len(stu.get('elementary', []))
    mid_count = len(stu.get('middle', []))
    high_count = len(stu.get('high', []))
    print(f"  Elementary data points: {elem_count:,}")
    print(f"  Middle data points: {mid_count:,}")
    print(f"  High data points: {high_count:,}")
    print(f"  Total student data points: {elem_count + mid_count + high_count:,}")
except Exception as e:
    print(f"  Error loading student data: {e}")

# 3. District 4 age breakdown
print("\n=== DISTRICT 4 AGE BREAKDOWN ===")
# Load SMD boundaries
with open('/opt/whovoted/public/data/mcallen_smd.json') as f:
    smd = json.load(f)

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

# Find District 4 geometry
d4_geom = None
for feat in smd['features']:
    name = feat['properties']['NAME']
    if '4' in name:
        d4_geom = feat['geometry']
        print(f"  Found: {name}")
        break

if d4_geom:
    rows = conn.execute(f"""
        SELECT v.birth_year, v.sex,
               CASE WHEN ve.vuid IS NOT NULL THEN 1 ELSE 0 END as voted
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL AND v.lng IS NOT NULL
    """, (ELECTION,) + ZIPS).fetchall()
    
    d4_age = {}
    d4_total = 0
    d4_voted = 0
    d4_young = 0
    d4_young_voted = 0
    
    # Sample to find D4 voters (check all)
    all_voters = conn.execute(f"""
        SELECT v.lat, v.lng, v.birth_year, v.sex,
               CASE WHEN ve.vuid IS NOT NULL THEN 1 ELSE 0 END as voted,
               CASE
                   WHEN LOWER(COALESCE(v.current_party,'')) LIKE '%democrat%' THEN 'Dem'
                   WHEN LOWER(COALESCE(v.current_party,'')) LIKE '%republican%' THEN 'Rep'
                   ELSE 'Other'
               END as party
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL AND v.lng IS NOT NULL
    """, (ELECTION,) + ZIPS).fetchall()
    
    for lat, lng, by, sex, voted, party in all_voters:
        if pip_geom(lng, lat, d4_geom):
            d4_total += 1
            if voted: d4_voted += 1
            if by and by > 0:
                age = 2026 - by
                if 18 <= age <= 45:
                    d4_young += 1
                    if voted: d4_young_voted += 1
                bucket = '18-35' if age <= 35 else '36-45' if age <= 45 else '46-55' if age <= 55 else '56-65' if age <= 65 else '65+'
                if bucket not in d4_age:
                    d4_age[bucket] = {'reg': 0, 'voted': 0}
                d4_age[bucket]['reg'] += 1
                if voted: d4_age[bucket]['voted'] += 1
    
    print(f"  D4 total: {d4_total}, voted: {d4_voted}")
    print(f"  D4 young (18-45): {d4_young} registered, {d4_young_voted} voted ({d4_young_voted/d4_young*100:.2f}%)" if d4_young else "")
    for bucket in ['18-35', '36-45', '46-55', '56-65', '65+']:
        if bucket in d4_age:
            a = d4_age[bucket]
            pct = a['voted']/a['reg']*100 if a['reg'] else 0
            print(f"  D4 {bucket}: {a['voted']}/{a['reg']} = {pct:.1f}%")

# 4. F-grade schools: how many registered voters are parents age (25-50)?
print("\n=== F-GRADE ZONES: PARENT-AGE VOTERS ===")
f_schools_elem = [c for c in elem['campuses'] if c['grade'] == 'F']
f_schools_ms = [c for c in ms['campuses'] if c['grade'] == 'F']
print(f"  F-grade elementary: {', '.join(c['name'] for c in f_schools_elem)}")
print(f"  F-grade middle: {', '.join(c['name'] for c in f_schools_ms)}")
total_f_reg = sum(c['registered'] for c in f_schools_elem) + sum(c['registered'] for c in f_schools_ms)
total_f_voted = sum(c['voted'] for c in f_schools_elem) + sum(c['voted'] for c in f_schools_ms)
print(f"  Combined F-grade zones: {total_f_voted} voted / {total_f_reg:,} registered = {total_f_voted/total_f_reg*100:.2f}%")

# 5. Compare north vs south
print("\n=== NORTH vs SOUTH (by latitude) ===")
# McAllen center is ~26.23. South is below that.
north_voted = 0; north_reg = 0; south_voted = 0; south_reg = 0
for lat, lng, by, sex, voted, party in all_voters:
    if lat >= 26.22:
        north_reg += 1
        if voted: north_voted += 1
    else:
        south_reg += 1
        if voted: south_voted += 1
np = north_voted/north_reg*100 if north_reg else 0
sp = south_voted/south_reg*100 if south_reg else 0
print(f"  North McAllen (above 26.22): {north_voted:,}/{north_reg:,} = {np:.2f}%")
print(f"  South McAllen (below 26.22): {south_voted:,}/{south_reg:,} = {sp:.2f}%")
print(f"  North/South ratio: {np/sp:.1f}x" if sp > 0 else "")

conn.close()
