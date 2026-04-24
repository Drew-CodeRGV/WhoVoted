#!/usr/bin/env python3
"""
Find the latitude cutoff that gives us the certified vote totals.
"""

import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'

TARGET_EARLY = 9876
TARGET_EDAY = 3754

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def point_in_polygon(lng, lat, geometry):
    gtype = geometry.get('type', '')
    coords = geometry.get('coordinates', [])
    if gtype == 'Polygon':
        return _point_in_ring(lng, lat, coords[0])
    elif gtype == 'MultiPolygon':
        return any(_point_in_ring(lng, lat, poly[0]) for poly in coords)
    return False

def _point_in_ring(lng, lat, ring):
    inside = False
    n = len(ring)
    p1_lng, p1_lat = ring[0]
    for i in range(1, n + 1):
        p2_lng, p2_lat = ring[i % n]
        if lat > min(p1_lat, p2_lat):
            if lat <= max(p1_lat, p2_lat):
                if lng <= max(p1_lng, p2_lng):
                    if p1_lat != p2_lat:
                        x_inters = (lat - p1_lat) * (p2_lng - p1_lng) / (p2_lat - p1_lat) + p1_lng
                    if p1_lng == p2_lng or lng <= x_inters:
                        inside = not inside
        p1_lng, p1_lat = p2_lng, p2_lat
    return inside

with open(DISTRICTS_FILE) as f:
    districts = json.load(f)['features']

cpct2 = next((d for d in districts if d['properties'].get('district_id') == 'CPct-2'), None)

cur.execute("""
    SELECT precinct, AVG(lat) as avg_lat, AVG(lng) as avg_lon
    FROM voters WHERE county = 'Hidalgo' AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""")

precincts_with_coords = []
for row in cur.fetchall():
    if point_in_polygon(row['avg_lon'], row['avg_lat'], cpct2['geometry']):
        precincts_with_coords.append({
            'precinct': row['precinct'],
            'lat': row['avg_lat'],
            'lng': row['avg_lon']
        })

# Get votes for all these precincts
all_precincts = [p['precinct'] for p in precincts_with_coords]
placeholders = ','.join('?' * len(all_precincts))

cur.execute(f"""
    SELECT 
        v.precinct,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'early-voting' THEN ve.vuid END) as dem_early,
        COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'election-day' THEN ve.vuid END) as dem_eday
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = 'Hidalgo' AND v.precinct IN ({placeholders})
    AND ve.election_date = '2026-03-03'
    AND ve.data_source = 'county-upload'
    GROUP BY v.precinct
""", all_precincts)

precinct_votes = {}
for row in cur.fetchall():
    precinct_votes[row['precinct']] = {
        'dem_early': row['dem_early'],
        'dem_eday': row['dem_eday']
    }

# Add votes to precinct data
for p in precincts_with_coords:
    votes = precinct_votes.get(p['precinct'], {'dem_early': 0, 'dem_eday': 0})
    p['dem_early'] = votes['dem_early']
    p['dem_eday'] = votes['dem_eday']

# Sort by latitude
precincts_with_coords.sort(key=lambda x: x['lat'])

print("="*80)
print("FINDING OPTIMAL LATITUDE CUTOFF")
print("="*80)

best_match = None
best_diff = float('inf')

# Try different cutoffs
for i in range(50, len(precincts_with_coords) - 50, 10):
    cutoff_lat = precincts_with_coords[i]['lat']
    filtered = [p for p in precincts_with_coords if p['lat'] <= cutoff_lat]
    
    early_sum = sum(p['dem_early'] for p in filtered)
    eday_sum = sum(p['dem_eday'] for p in filtered)
    
    diff = abs(early_sum - TARGET_EARLY) + abs(eday_sum - TARGET_EDAY)
    
    if diff < best_diff:
        best_diff = diff
        best_match = {
            'cutoff_lat': cutoff_lat,
            'num_precincts': len(filtered),
            'early': early_sum,
            'eday': eday_sum,
            'diff': diff
        }
    
    if i % 50 == 0:
        print(f"Lat <= {cutoff_lat:.4f}: {len(filtered)} precincts, Early={early_sum:,}, EDay={eday_sum:,}, Diff={diff}")

print("\n" + "="*80)
print("BEST MATCH")
print("="*80)
print(f"Latitude cutoff: {best_match['cutoff_lat']:.4f}")
print(f"Number of precincts: {best_match['num_precincts']}")
print(f"DEM Early: {best_match['early']:,} (target: {TARGET_EARLY:,}, diff: {abs(best_match['early']-TARGET_EARLY)})")
print(f"DEM EDay: {best_match['eday']:,} (target: {TARGET_EDAY:,}, diff: {abs(best_match['eday']-TARGET_EDAY)})")
print(f"Total difference: {best_match['diff']}")

# Try finer granularity around best match
print("\n" + "="*80)
print("FINE-TUNING")
print("="*80)

best_idx = next(i for i, p in enumerate(precincts_with_coords) if p['lat'] > best_match['cutoff_lat']) - 1

for i in range(max(0, best_idx - 20), min(len(precincts_with_coords), best_idx + 20)):
    cutoff_lat = precincts_with_coords[i]['lat']
    filtered = [p for p in precincts_with_coords if p['lat'] <= cutoff_lat]
    
    early_sum = sum(p['dem_early'] for p in filtered)
    eday_sum = sum(p['dem_eday'] for p in filtered)
    diff = abs(early_sum - TARGET_EARLY) + abs(eday_sum - TARGET_EDAY)
    
    if diff < best_diff:
        best_diff = diff
        best_match = {
            'cutoff_lat': cutoff_lat,
            'num_precincts': len(filtered),
            'early': early_sum,
            'eday': eday_sum,
            'diff': diff,
            'precincts': [p['precinct'] for p in filtered]
        }

print(f"\nOPTIMAL: Lat <= {best_match['cutoff_lat']:.4f}")
print(f"Precincts: {best_match['num_precincts']}")
print(f"Early: {best_match['early']:,}, EDay: {best_match['eday']:,}")
print(f"Total diff: {best_match['diff']}")

if best_match['diff'] < 200:
    print("\n✓ FOUND MATCHING BOUNDARY!")
    print(f"\nCorrect precincts ({len(best_match['precincts'])}):")
    print(', '.join(sorted(best_match['precincts'])[:50]))
    if len(best_match['precincts']) > 50:
        print(f"... and {len(best_match['precincts']) - 50} more")

conn.close()
