#!/usr/bin/env python3
"""Direct DB verification of new voter age/gender for HD-41.

This simulates what the district-stats API does: takes VUIDs from the GeoJSON
that fall within HD-41 boundary, then queries new voters by age/gender.
We'll use the same approach the frontend uses - read the GeoJSON, do point-in-polygon.
"""
import json
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICT_FILE = '/opt/whovoted/public/data/districts.json'

conn = sqlite3.connect(DB_PATH)

# Load district boundaries
with open(DISTRICT_FILE) as f:
    districts = json.load(f)

# Find HD-41
hd41 = None
for feat in districts.get('features', []):
    if feat['properties'].get('district_id') == 'HD-41':
        hd41 = feat
        break

if not hd41:
    print("HD-41 not found in districts.json")
    exit(1)

print(f"Found HD-41: {hd41['properties'].get('district_name')}")

# Simple point-in-polygon (ray casting)
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

def point_in_feature(lng, lat, feature):
    geom = feature['geometry']
    if geom['type'] == 'Polygon':
        for ring in geom['coordinates']:
            if point_in_polygon(lng, lat, ring):
                return True
    elif geom['type'] == 'MultiPolygon':
        for polygon in geom['coordinates']:
            for ring in polygon:
                if point_in_polygon(lng, lat, ring):
                    return True
    return False

# Load 2026 GeoJSON files to get voter coordinates
print("Loading 2026 GeoJSON files...")
vuids_in_district = set()

for party in ['democratic', 'republican']:
    filepath = f'/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_{party}_cumulative_ev.json'
    try:
        with open(filepath) as f:
            data = json.load(f)
        for feat in data.get('features', []):
            geom = feat.get('geometry')
            if not geom or geom.get('type') != 'Point':
                continue
            lng, lat = geom['coordinates']
            vuid = feat['properties'].get('vuid', '')
            if vuid and point_in_feature(lng, lat, hd41):
                vuids_in_district.add(vuid)
    except Exception as e:
        print(f"  Error loading {filepath}: {e}")

print(f"Found {len(vuids_in_district):,} voters in HD-41")

# Now query new voters by age/gender directly from DB
vuids_list = list(vuids_in_district)
new_age_gender = {}
new_total = 0

for i in range(0, len(vuids_list), 999):
    chunk = vuids_list[i:i+999]
    ph = ','.join(['?' for _ in chunk])
    rows = conn.execute(f"""
        SELECT
            CASE
                WHEN v.birth_year BETWEEN 2002 AND 2008 THEN '18-24'
                WHEN v.birth_year BETWEEN 1992 AND 2001 THEN '25-34'
                WHEN v.birth_year BETWEEN 1982 AND 1991 THEN '35-44'
                WHEN v.birth_year BETWEEN 1972 AND 1981 THEN '45-54'
                WHEN v.birth_year BETWEEN 1962 AND 1971 THEN '55-64'
                WHEN v.birth_year BETWEEN 1952 AND 1961 THEN '65-74'
                WHEN v.birth_year > 0 AND v.birth_year < 1952 THEN '75+'
                ELSE 'Unknown'
            END as age_group,
            v.sex,
            COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03' AND ve.vuid IN ({ph})
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
        GROUP BY age_group, v.sex
    """, chunk).fetchall()
    for row in rows:
        ag, sex, cnt = row[0], row[1] or 'U', row[2]
        if ag not in new_age_gender:
            new_age_gender[ag] = {'total': 0, 'female': 0, 'male': 0}
        new_age_gender[ag]['total'] += cnt
        new_total += cnt
        if sex == 'F':
            new_age_gender[ag]['female'] += cnt
        elif sex == 'M':
            new_age_gender[ag]['male'] += cnt

print(f"\n=== HD-41 New Voters by Age/Gender (Direct DB) ===")
print(f"Total new voters: {new_total:,}")
order = ['18-24','25-34','35-44','45-54','55-64','65-74','75+','Unknown']
for ag in order:
    g = new_age_gender.get(ag, {})
    t = g.get('total', 0)
    f = g.get('female', 0)
    m = g.get('male', 0)
    marker = ' <<<' if t > 0 else ''
    print(f"  {ag:>8}: {t:>5,} total  (♀{f:>5,}  ♂{m:>5,}){marker}")

# Show top 2
sorted_groups = sorted([(ag, new_age_gender.get(ag, {}).get('total', 0)) for ag in order if new_age_gender.get(ag, {}).get('total', 0) > 0], key=lambda x: -x[1])
print(f"\nTop 2 age groups:")
for ag, total in sorted_groups[:2]:
    g = new_age_gender[ag]
    print(f"  {ag}: {total:,} total (♀{g['female']:,} ♂{g['male']:,})")

conn.close()
