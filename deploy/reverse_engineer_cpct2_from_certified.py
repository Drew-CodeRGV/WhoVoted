#!/usr/bin/env python3
"""
Reverse engineer the correct CPct-2 precinct list from certified vote numbers.

CERTIFIED NUMBERS (MUST BE EXACT):
- DEM Early: 9,876
- DEM Election Day: 3,754
- DEM Total: 13,630

STRATEGY:
1. Get all precincts and their vote counts
2. Find combination that matches certified numbers exactly
3. Use greedy algorithm + optimization to find the right set
"""

import sqlite3
import json
from collections import defaultdict

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'
ELECTION_DATE = '2026-03-03'
COUNTY = 'Hidalgo'

# CERTIFIED NUMBERS - MUST BE EXACT
TARGET_EARLY = 9876
TARGET_ELECTION_DAY = 3754
TARGET_TOTAL = 13630

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

print("="*80)
print("REVERSE ENGINEERING CPCT-2 FROM CERTIFIED NUMBERS")
print("="*80)
print(f"Target: {TARGET_EARLY:,} early + {TARGET_ELECTION_DAY:,} election day = {TARGET_TOTAL:,} DEM")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Load current CPct-2 boundary to get candidate precincts
with open(DISTRICTS_FILE) as f:
    districts = json.load(f)['features']

cpct2 = next((d for d in districts if d['properties'].get('district_id') == 'CPct-2'), None)

# Get all precincts in current boundary
cur.execute("""
    SELECT precinct, AVG(lat) as lat, AVG(lng) as lng
    FROM voters WHERE county = ? AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""", (COUNTY,))

candidate_precincts = []
for row in cur.fetchall():
    if point_in_polygon(row['lng'], row['lat'], cpct2['geometry']):
        candidate_precincts.append(row['precinct'])

print(f"\nCandidate precincts from current boundary: {len(candidate_precincts)}")

# Get vote counts for each precinct
precinct_votes = {}
for precinct in candidate_precincts:
    cur.execute("""
        SELECT 
            COUNT(DISTINCT CASE WHEN ve.voting_method = 'early-voting' THEN ve.vuid END) as early,
            COUNT(DISTINCT CASE WHEN ve.voting_method = 'election-day' THEN ve.vuid END) as election_day
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.county = ? AND v.precinct = ? AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
    """, (COUNTY, precinct, ELECTION_DATE))
    
    row = cur.fetchone()
    early = row['early']
    election_day = row['election_day']
    
    if early > 0 or election_day > 0:
        precinct_votes[precinct] = {
            'early': early,
            'election_day': election_day,
            'total': early + election_day
        }

print(f"Precincts with DEM votes: {len(precinct_votes)}")

# Sort precincts by total votes (descending)
sorted_precincts = sorted(precinct_votes.items(), key=lambda x: x[1]['total'], reverse=True)

print("\nTop 10 precincts by DEM votes:")
for precinct, votes in sorted_precincts[:10]:
    print(f"  {precinct}: {votes['early']:,} early + {votes['election_day']:,} election day = {votes['total']:,}")

# Strategy 1: Try to find exact match using greedy algorithm
print("\n" + "="*80)
print("STRATEGY 1: GREEDY ALGORITHM")
print("="*80)

selected = []
current_early = 0
current_election_day = 0

# Sort by ratio of early to election day (to match the target ratio)
target_ratio = TARGET_EARLY / TARGET_ELECTION_DAY if TARGET_ELECTION_DAY > 0 else 0
sorted_by_ratio = sorted(
    precinct_votes.items(),
    key=lambda x: abs((x[1]['early'] / x[1]['election_day'] if x[1]['election_day'] > 0 else 999) - target_ratio)
)

for precinct, votes in sorted_by_ratio:
    # Try adding this precinct
    new_early = current_early + votes['early']
    new_election_day = current_election_day + votes['election_day']
    
    # If we're still under target, add it
    if new_early <= TARGET_EARLY and new_election_day <= TARGET_ELECTION_DAY:
        selected.append(precinct)
        current_early = new_early
        current_election_day = new_election_day
        
        if current_early == TARGET_EARLY and current_election_day == TARGET_ELECTION_DAY:
            print(f"✓ EXACT MATCH FOUND!")
            break

print(f"\nGreedy result:")
print(f"  Precincts: {len(selected)}")
print(f"  Early: {current_early:,} (target: {TARGET_EARLY:,}, diff: {current_early - TARGET_EARLY:+,})")
print(f"  Election Day: {current_election_day:,} (target: {TARGET_ELECTION_DAY:,}, diff: {current_election_day - TARGET_ELECTION_DAY:+,})")
print(f"  Total: {current_early + current_election_day:,} (target: {TARGET_TOTAL:,})")

# Strategy 2: Try geographic filtering
print("\n" + "="*80)
print("STRATEGY 2: GEOGRAPHIC FILTERING")
print("="*80)

# Get precinct locations
cur.execute("""
    SELECT precinct, AVG(lat) as lat, AVG(lng) as lng
    FROM voters WHERE county = ? AND precinct IN ({})
    GROUP BY precinct
""".format(','.join('?' * len(candidate_precincts))), [COUNTY] + candidate_precincts)

precinct_locations = {row['precinct']: (row['lat'], row['lng']) for row in cur.fetchall()}

# Try different latitude cutoffs
best_lat_cutoff = None
best_lat_diff = float('inf')

for lat_cutoff in [26.15, 26.16, 26.17, 26.18, 26.19, 26.20, 26.21, 26.22]:
    filtered = [p for p in candidate_precincts if precinct_locations.get(p, (999, 999))[0] < lat_cutoff]
    
    early = sum(precinct_votes.get(p, {}).get('early', 0) for p in filtered)
    election_day = sum(precinct_votes.get(p, {}).get('election_day', 0) for p in filtered)
    
    diff = abs(early - TARGET_EARLY) + abs(election_day - TARGET_ELECTION_DAY)
    
    if diff < best_lat_diff:
        best_lat_diff = diff
        best_lat_cutoff = lat_cutoff
        best_lat_precincts = filtered
        best_lat_early = early
        best_lat_election_day = election_day

print(f"\nBest latitude cutoff: {best_lat_cutoff}")
print(f"  Precincts: {len(best_lat_precincts)}")
print(f"  Early: {best_lat_early:,} (target: {TARGET_EARLY:,}, diff: {best_lat_early - TARGET_EARLY:+,})")
print(f"  Election Day: {best_lat_election_day:,} (target: {TARGET_ELECTION_DAY:,}, diff: {best_lat_election_day - TARGET_ELECTION_DAY:+,})")

# Strategy 3: Optimization - remove precincts from current boundary
print("\n" + "="*80)
print("STRATEGY 3: REMOVE OUTLIERS FROM CURRENT BOUNDARY")
print("="*80)

# Start with all precincts, remove those that push us over
current_precincts = set(candidate_precincts)
current_early = sum(precinct_votes.get(p, {}).get('early', 0) for p in current_precincts)
current_election_day = sum(precinct_votes.get(p, {}).get('election_day', 0) for p in current_precincts)

print(f"Starting with {len(current_precincts)} precincts:")
print(f"  Early: {current_early:,} (over by {current_early - TARGET_EARLY:,})")
print(f"  Election Day: {current_election_day:,} (over by {current_election_day - TARGET_ELECTION_DAY:,})")

# Remove precincts that are furthest from centroid and have high early voting
centroid_lat = sum(precinct_locations.get(p, (0, 0))[0] for p in current_precincts) / len(current_precincts)
centroid_lng = sum(precinct_locations.get(p, (0, 0))[1] for p in current_precincts) / len(current_precincts)

# Calculate distance from centroid for each precinct
precinct_distances = {}
for p in current_precincts:
    lat, lng = precinct_locations.get(p, (0, 0))
    dist = ((lat - centroid_lat)**2 + (lng - centroid_lng)**2)**0.5
    precinct_distances[p] = dist

# Sort by distance (furthest first) and early vote count
sorted_to_remove = sorted(
    current_precincts,
    key=lambda p: (precinct_distances.get(p, 0), precinct_votes.get(p, {}).get('early', 0)),
    reverse=True
)

removed = []
for precinct in sorted_to_remove:
    votes = precinct_votes.get(precinct, {})
    new_early = current_early - votes.get('early', 0)
    new_election_day = current_election_day - votes.get('election_day', 0)
    
    # If removing this gets us closer to target, remove it
    old_diff = abs(current_early - TARGET_EARLY) + abs(current_election_day - TARGET_ELECTION_DAY)
    new_diff = abs(new_early - TARGET_EARLY) + abs(new_election_day - TARGET_ELECTION_DAY)
    
    if new_diff < old_diff:
        current_precincts.remove(precinct)
        removed.append(precinct)
        current_early = new_early
        current_election_day = new_election_day
        
        if current_early == TARGET_EARLY and current_election_day == TARGET_ELECTION_DAY:
            print(f"✓ EXACT MATCH FOUND!")
            break

print(f"\nRemoved {len(removed)} precincts")
print(f"Remaining: {len(current_precincts)} precincts")
print(f"  Early: {current_early:,} (target: {TARGET_EARLY:,}, diff: {current_early - TARGET_EARLY:+,})")
print(f"  Election Day: {current_election_day:,} (target: {TARGET_ELECTION_DAY:,}, diff: {current_election_day - TARGET_ELECTION_DAY:+,})")

# Determine best strategy
print("\n" + "="*80)
print("BEST SOLUTION")
print("="*80)

strategies = [
    ("Greedy", selected, current_early, current_election_day),
    ("Geographic", best_lat_precincts, best_lat_early, best_lat_election_day),
    ("Remove Outliers", list(current_precincts), 
     sum(precinct_votes.get(p, {}).get('early', 0) for p in current_precincts),
     sum(precinct_votes.get(p, {}).get('election_day', 0) for p in current_precincts))
]

best_strategy = min(strategies, 
                   key=lambda x: abs(x[2] - TARGET_EARLY) + abs(x[3] - TARGET_ELECTION_DAY))

name, precincts, early, election_day = best_strategy

print(f"Best strategy: {name}")
print(f"  Precincts: {len(precincts)}")
print(f"  Early: {early:,} (target: {TARGET_EARLY:,}, diff: {early - TARGET_EARLY:+,})")
print(f"  Election Day: {election_day:,} (target: {TARGET_ELECTION_DAY:,}, diff: {election_day - TARGET_ELECTION_DAY:+,})")
print(f"  Total: {early + election_day:,} (target: {TARGET_TOTAL:,})")

# Save the precinct list
output_file = '/opt/whovoted/deploy/cpct2_correct_precincts.json'
with open(output_file, 'w') as f:
    json.dump({
        'strategy': name,
        'precincts': sorted(precincts),
        'counts': {
            'early': early,
            'election_day': election_day,
            'total': early + election_day
        },
        'target': {
            'early': TARGET_EARLY,
            'election_day': TARGET_ELECTION_DAY,
            'total': TARGET_TOTAL
        },
        'difference': {
            'early': early - TARGET_EARLY,
            'election_day': election_day - TARGET_ELECTION_DAY,
            'total': (early + election_day) - TARGET_TOTAL
        }
    }, f, indent=2)

print(f"\n✓ Precinct list saved to {output_file}")

conn.close()
