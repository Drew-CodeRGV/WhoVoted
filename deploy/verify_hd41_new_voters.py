#!/usr/bin/env python3
"""Verify the 'new voter' count for HD-41 district.
A 'new voter' = a VUID that has NO prior election record before 2026-03-03
in the voter_elections table (with a non-empty party_voted).
"""
import sqlite3
import json

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row

# Load districts.json to get HD-41 boundary
with open('/opt/whovoted/public/data/districts.json') as f:
    districts = json.load(f)

hd41 = None
for feat in districts['features']:
    if feat['properties']['district_id'] == 'HD-41':
        hd41 = feat
        break

if not hd41:
    print("HD-41 not found in districts.json!")
    exit(1)

print(f"District: {hd41['properties']['district_name']}")
print(f"Geometry type: {hd41['geometry']['type']}")

# Load the current 2026 GeoJSON to get voter coordinates
# Find the 2026 map_data file
import glob
map_files = glob.glob('/opt/whovoted/public/data/map_data_*2026*.json')
print(f"\n2026 map data files: {map_files}")

all_voters = []
for mf in map_files:
    with open(mf) as f:
        data = json.load(f)
    all_voters.extend(data.get('features', []))
print(f"Total voters in GeoJSON: {len(all_voters)}")

# Point-in-polygon (ray casting)
def point_in_polygon(x, y, polygon):
    inside = False
    n = len(polygon)
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
        return point_in_polygon(lng, lat, geom['coordinates'][0])
    elif geom['type'] == 'MultiPolygon':
        return any(point_in_polygon(lng, lat, poly[0]) for poly in geom['coordinates'])
    return False

# Find voters inside HD-41
print("\nFinding voters inside HD-41 boundary...")
voters_in_district = []
for v in all_voters:
    if not v.get('geometry') or not v['geometry'].get('coordinates'):
        continue
    lng, lat = v['geometry']['coordinates']
    if lat == 0 and lng == 0:
        continue
    if point_in_feature(lng, lat, hd41):
        voters_in_district.append(v)

print(f"Voters inside HD-41: {len(voters_in_district)}")

# Get VUIDs
vuids = [v['properties'].get('vuid', '') for v in voters_in_district if v['properties'].get('vuid')]
vuids = [v for v in vuids if v]
print(f"VUIDs with values: {len(vuids)}")

# Now check how many are "new" (no prior election record)
print("\n=== Checking 'new voter' definition ===")
new_count = 0
new_voters_sample = []
not_new_count = 0

for vuid in vuids:
    # Check if this VUID has any election record before 2026-03-03
    prior = conn.execute("""
        SELECT COUNT(*) FROM voter_elections 
        WHERE vuid = ? AND election_date < '2026-03-03'
            AND party_voted != '' AND party_voted IS NOT NULL
    """, (vuid,)).fetchone()[0]
    
    if prior == 0:
        new_count += 1
        if len(new_voters_sample) < 10:
            # Get their 2026 record
            rec = conn.execute("""
                SELECT party_voted FROM voter_elections 
                WHERE vuid = ? AND election_date = '2026-03-03'
            """, (vuid,)).fetchone()
            new_voters_sample.append({
                'vuid': vuid,
                'party_2026': rec['party_voted'] if rec else 'N/A'
            })
    else:
        not_new_count += 1

print(f"\nNew voters (no prior record): {new_count}")
print(f"Returning voters (have prior record): {not_new_count}")
print(f"Total: {new_count + not_new_count}")

print(f"\n=== Sample of 10 'new' voters ===")
for nv in new_voters_sample:
    # Show ALL their election records
    all_recs = conn.execute("""
        SELECT election_date, party_voted, voting_method 
        FROM voter_elections WHERE vuid = ? ORDER BY election_date
    """, (nv['vuid'],)).fetchall()
    print(f"  VUID {nv['vuid']}:")
    for r in all_recs:
        print(f"    {r['election_date']}: {r['party_voted']} ({r['voting_method']})")
    if len(all_recs) == 1:
        print(f"    ^ Only 1 record — truly first-time in our data")

# Also verify via the SQL used in the API endpoint
print(f"\n=== Verify via API-style SQL (chunked) ===")
api_new = 0
for i in range(0, len(vuids), 999):
    chunk = vuids[i:i+999]
    placeholders = ','.join(['?' for _ in chunk])
    api_new += conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        WHERE ve.election_date = '2026-03-03' AND ve.vuid IN ({placeholders})
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    """, chunk).fetchone()[0]

print(f"API-style new voter count: {api_new}")
if api_new == new_count:
    print("✅ Matches individual check")
else:
    print(f"❌ Mismatch! Individual: {new_count}, API-style: {api_new}")

# County-wide context
total_2026 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03'").fetchone()[0]
total_new_county = conn.execute("""
    SELECT COUNT(*) FROM voter_elections ve
    WHERE ve.election_date = '2026-03-03'
      AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
          WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
            AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
""").fetchone()[0]
print(f"\n=== County-wide context ===")
print(f"Total 2026 voters: {total_2026}")
print(f"Total new voters county-wide: {total_new_county} ({round(total_new_county/total_2026*100,1)}%)")
print(f"HD-41 new voters: {new_count} ({round(new_count/len(vuids)*100,1)}% of HD-41 voters)")
print(f"HD-41 share of county new voters: {round(new_count/total_new_county*100,1)}%")

conn.close()
