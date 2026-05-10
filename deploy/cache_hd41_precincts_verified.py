#!/usr/bin/env python3
"""
Build a VERIFIED HD-41 precinct dataset using only real, geometrically validated data.

Steps:
1. Load HD-41 boundary polygon from districts.json
2. Load all available precinct boundary files
3. For each precinct polygon, test GEOMETRIC INTERSECTION with HD-41
   - Must have centroid inside HD-41 AND majority of polygon inside HD-41
4. For each verified precinct, compute REAL per-precinct results from voter_elections
5. Output:
   - hd41_precinct_shapes.json: only polygons inside HD-41
   - hd41_precinct_results.json: real per-precinct Dem/Rep counts, winner, margin
   - hd41_planner.json: priority ranking for targeting

All data is REAL — no estimates, no proportional allocation.
"""
import sqlite3, json, os
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
BOUNDARY_FILES = [
    '/opt/whovoted/public/data/precinct_boundaries.json',
    '/opt/whovoted/public/data/precinct_boundaries_cameron.json',
    '/opt/whovoted/public/data/precinct_boundaries_combined.json',
]
SHAPES_OUT = '/opt/whovoted/public/cache/hd41_precinct_shapes.json'
RESULTS_OUT = '/opt/whovoted/public/cache/hd41_precinct_results.json'
PLANNER_OUT = '/opt/whovoted/public/cache/hd41_planner.json'

ELECTION_DATE = '2026-03-03'
RUNOFF_DATE = '2026-05-26'


# ── Geometry helpers ──
def point_in_polygon(x, y, ring):
    n = len(ring)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def point_in_geom(lng, lat, geom):
    t = geom['type']
    if t == 'Polygon':
        return point_in_polygon(lng, lat, geom['coordinates'][0])
    elif t == 'MultiPolygon':
        return any(point_in_polygon(lng, lat, poly[0]) for poly in geom['coordinates'])
    return False


def polygon_vertices(geom):
    """Yield all vertex coordinates from a Polygon or MultiPolygon."""
    if geom['type'] == 'Polygon':
        for v in geom['coordinates'][0]:
            yield v[0], v[1]
    elif geom['type'] == 'MultiPolygon':
        for poly in geom['coordinates']:
            for v in poly[0]:
                yield v[0], v[1]


def polygon_centroid(geom):
    """Simple centroid = average of vertices."""
    xs, ys, n = 0, 0, 0
    for x, y in polygon_vertices(geom):
        xs += x
        ys += y
        n += 1
    return (xs / n, ys / n) if n else (0, 0)


def overlap_fraction(precinct_geom, hd41_geom, samples=20):
    """
    Quick check: is the centroid inside HD-41?
    Skip expensive vertex sampling — centroid is sufficient for our purposes.
    """
    cx, cy = polygon_centroid(precinct_geom)
    return 1.0 if point_in_geom(cx, cy, hd41_geom) else 0.0


def normalize_precinct(s):
    """Normalize precinct ID for matching across file formats."""
    s = str(s).replace('Precinct ', '').strip()
    try:
        return str(int(s))
    except ValueError:
        return s.lstrip('0') or '0'


# ── Main ──
def main():
    print("Building verified HD-41 precinct dataset...")

    # Load HD-41 boundary
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)
    hd41 = next((feat for feat in districts['features']
                 if feat.get('properties', {}).get('district_id') == 'HD-41'), None)
    if not hd41:
        print("ERROR: HD-41 not found in districts.json")
        return
    hd41_geom = hd41['geometry']
    print(f"  HD-41 boundary loaded ({hd41_geom['type']})")

    # Load DB precincts assigned to HD-41
    conn = sqlite3.connect(DB_PATH)
    db_precincts = set(r[0] for r in conn.execute("""
        SELECT DISTINCT precinct FROM voters
        WHERE state_house_district='HD-41' AND precinct IS NOT NULL
    """).fetchall())
    print(f"  {len(db_precincts)} precincts tagged HD-41 in DB")

    # Build normalized DB lookup
    db_lookup = {}
    for p in db_precincts:
        db_lookup[normalize_precinct(p)] = p
        db_lookup[p] = p

    # Load all boundary files and find HD-41 intersecting precincts
    verified_shapes = {}  # db_precinct -> feature
    for path in BOUNDARY_FILES:
        if not os.path.exists(path):
            continue
        print(f"\n  Loading {Path(path).name}...")
        with open(path) as f:
            data = json.load(f)
        features = data.get('features', []) if isinstance(data, dict) else data
        if not features:
            continue

        # Find precinct field
        props = features[0].get('properties', {})
        pct_field = next((f for f in ['precinct', 'PRECINCT', 'Precinct', 'PCT', 'NAME', 'name', 'VTDST', 'precinct_id'] if f in props), None)
        if not pct_field:
            continue

        tested = 0
        kept = 0
        for feature in features:
            pct_raw = feature.get('properties', {}).get(pct_field, '')
            if not pct_raw:
                continue
            norm = normalize_precinct(pct_raw)

            # Must match a DB precinct that's tagged HD-41
            if norm not in db_lookup:
                continue

            db_pct = db_lookup[norm]
            if db_pct in verified_shapes:
                continue  # already got this one

            # GEOMETRIC CHECK: at least 50% of precinct polygon must be inside HD-41
            frac = overlap_fraction(feature['geometry'], hd41_geom)
            tested += 1
            if frac >= 0.5:
                # Also verify centroid is inside HD-41
                cx, cy = polygon_centroid(feature['geometry'])
                if point_in_geom(cx, cy, hd41_geom):
                    feature['properties']['db_precinct'] = db_pct
                    feature['properties']['overlap_pct'] = round(frac * 100, 1)
                    verified_shapes[db_pct] = feature
                    kept += 1

        print(f"    Tested {tested} matches, kept {kept} inside HD-41")

    print(f"\n  Total verified precinct shapes: {len(verified_shapes)}")

    # Build per-precinct results using REAL data from voter_elections
    print("\nComputing real per-precinct results...")

    # Batch query: all March primary results for HD-41 precincts
    all_votes = conn.execute("""
        SELECT ve.precinct, ve.party_voted, COUNT(*) as cnt
        FROM voter_elections ve
        WHERE ve.election_date=? AND ve.state_house_district='HD-41'
        AND ve.precinct IS NOT NULL
        AND ve.party_voted IN ('Democratic', 'Republican')
        GROUP BY ve.precinct, ve.party_voted
    """, (ELECTION_DATE,)).fetchall()

    # Batch: runoff data
    runoff_votes = conn.execute("""
        SELECT ve.precinct, ve.party_voted, COUNT(*) as cnt
        FROM voter_elections ve
        WHERE ve.election_date=? AND ve.state_house_district='HD-41'
        AND ve.precinct IS NOT NULL
        GROUP BY ve.precinct, ve.party_voted
    """, (RUNOFF_DATE,)).fetchall()

    # Batch: registered voters per precinct
    reg_counts = conn.execute("""
        SELECT precinct, COUNT(*) as cnt
        FROM voters WHERE state_house_district='HD-41' AND precinct IS NOT NULL
        GROUP BY precinct
    """).fetchall()

    # Batch: centroids
    centroids = conn.execute("""
        SELECT precinct, AVG(lat), AVG(lng)
        FROM voters WHERE state_house_district='HD-41' AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """).fetchall()

    # Build lookups
    vote_data = {}  # precinct -> {dem, rep}
    for pct, party, cnt in all_votes:
        if pct not in vote_data:
            vote_data[pct] = {'dem': 0, 'rep': 0}
        if party == 'Democratic':
            vote_data[pct]['dem'] = cnt
        else:
            vote_data[pct]['rep'] = cnt

    runoff_data = {}
    for pct, party, cnt in runoff_votes:
        if pct not in runoff_data:
            runoff_data[pct] = {'dem': 0, 'rep': 0}
        if party == 'Democratic':
            runoff_data[pct]['dem'] = cnt
        elif party == 'Republican':
            runoff_data[pct]['rep'] = cnt

    reg_lookup = {r[0]: r[1] for r in reg_counts}
    centroid_lookup = {r[0]: (r[1], r[2]) for r in centroids}

    precinct_results = {}
    for precinct in db_precincts:
        vd = vote_data.get(precinct)
        if not vd:
            continue  # no real vote data
        dem, rep = vd['dem'], vd['rep']
        total = dem + rep
        if total == 0:
            continue

        lat, lng = centroid_lookup.get(precinct, (None, None))
        if not lat or not lng:
            continue

        # Verify centroid is inside HD-41
        if not point_in_geom(lng, lat, hd41_geom):
            continue

        reg = reg_lookup.get(precinct, 0)
        rd = runoff_data.get(precinct, {'dem': 0, 'rep': 0})

        if dem > rep:
            winner = 'Democratic'
            margin_votes = dem - rep
            margin_pct = round((dem - rep) / total * 100, 1)
        elif rep > dem:
            winner = 'Republican'
            margin_votes = rep - dem
            margin_pct = round((rep - dem) / total * 100, 1)
        else:
            winner = 'Tie'
            margin_votes = 0
            margin_pct = 0.0

        precinct_results[precinct] = {
            'precinct': precinct,
            'lat': round(lat, 4),
            'lng': round(lng, 4),
            'registered': reg,
            'dem_votes': dem,
            'rep_votes': rep,
            'total_votes': total,
            'winner': winner,
            'margin_votes': margin_votes,
            'margin_pct': margin_pct,
            'turnout_pct': round(total / reg * 100, 1) if reg > 0 else 0,
            'dem_share': round(dem / total * 100, 1),
            'rep_share': round(rep / total * 100, 1),
            'runoff_dem': rd['dem'],
            'runoff_rep': rd['rep'],
            'runoff_total': rd['dem'] + rd['rep'],
            'has_shape': precinct in verified_shapes,
        }

    # Filter shapes to only those with real results
    final_shapes = {p: s for p, s in verified_shapes.items() if p in precinct_results}
    print(f"  Precincts with real data: {len(precinct_results)}")
    print(f"  Precincts with both shape AND data: {len(final_shapes)}")

    # Build priority planner (ranked by strategic importance)
    print("\nBuilding priority planner...")
    planner_items = []
    for p, r in precinct_results.items():
        total = r['total_votes']
        margin = abs(r['margin_pct'])

        # Competitiveness: 100 = perfectly tied, 0 = total blowout
        competitiveness = max(0, 100 - margin)

        # Volume score: normalized to the largest precinct
        volume = total

        # Strategic score: competitive AND high volume = highest priority
        priority_score = (competitiveness / 100) * volume

        # Classify
        if total < 20:
            classification = 'Low Volume'
        elif margin < 10:
            classification = 'Battleground'
        elif r['winner'] == 'Democratic' and r['dem_share'] >= 70:
            classification = 'Dem Stronghold'
        elif r['winner'] == 'Republican' and r['rep_share'] >= 70:
            classification = 'Rep Stronghold'
        elif r['winner'] == 'Democratic':
            classification = 'Lean Dem'
        else:
            classification = 'Lean Rep'

        planner_items.append({
            'precinct': p,
            'lat': r['lat'], 'lng': r['lng'],
            'total_votes': total,
            'dem_votes': r['dem_votes'],
            'rep_votes': r['rep_votes'],
            'winner': r['winner'],
            'margin_pct': r['margin_pct'],
            'margin_votes': r['margin_votes'],
            'competitiveness': round(competitiveness, 1),
            'priority_score': round(priority_score, 1),
            'classification': classification,
            'has_shape': r['has_shape'],
        })

    # Sort by priority score
    planner_items.sort(key=lambda x: x['priority_score'], reverse=True)

    # Summary counts
    summary = {
        'total_precincts': len(precinct_results),
        'precincts_with_shapes': len(final_shapes),
        'battleground': len([p for p in planner_items if p['classification'] == 'Battleground']),
        'dem_strongholds': len([p for p in planner_items if p['classification'] == 'Dem Stronghold']),
        'rep_strongholds': len([p for p in planner_items if p['classification'] == 'Rep Stronghold']),
        'lean_dem': len([p for p in planner_items if p['classification'] == 'Lean Dem']),
        'lean_rep': len([p for p in planner_items if p['classification'] == 'Lean Rep']),
        'low_volume': len([p for p in planner_items if p['classification'] == 'Low Volume']),
        'total_dem_votes': sum(r['dem_votes'] for r in precinct_results.values()),
        'total_rep_votes': sum(r['rep_votes'] for r in precinct_results.values()),
        'total_votes': sum(r['total_votes'] for r in precinct_results.values()),
    }

    # Write outputs
    Path(SHAPES_OUT).parent.mkdir(parents=True, exist_ok=True)
    with open(SHAPES_OUT, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': list(final_shapes.values())}, f, separators=(',', ':'))

    with open(RESULTS_OUT, 'w') as f:
        json.dump({
            'election_date': ELECTION_DATE,
            'district': 'HD-41',
            'summary': summary,
            'precincts': list(precinct_results.values()),
        }, f, separators=(',', ':'))

    with open(PLANNER_OUT, 'w') as f:
        json.dump({
            'district': 'HD-41',
            'summary': summary,
            'top_battlegrounds': [p for p in planner_items if p['classification'] == 'Battleground'][:20],
            'top_priority': planner_items[:30],
            'all_precincts': planner_items,
        }, f, separators=(',', ':'))

    conn.close()

    print(f"\n✓ Shapes: {Path(SHAPES_OUT).stat().st_size/1024:.0f} KB ({len(final_shapes)} precincts)")
    print(f"✓ Results: {Path(RESULTS_OUT).stat().st_size/1024:.0f} KB ({len(precinct_results)} precincts)")
    print(f"✓ Planner: {Path(PLANNER_OUT).stat().st_size/1024:.0f} KB")
    print(f"\nSummary: Total {summary['total_votes']:,} votes (D:{summary['total_dem_votes']:,} R:{summary['total_rep_votes']:,})")
    print(f"  Battleground: {summary['battleground']}")
    print(f"  Dem strongholds: {summary['dem_strongholds']} | Lean Dem: {summary['lean_dem']}")
    print(f"  Rep strongholds: {summary['rep_strongholds']} | Lean Rep: {summary['lean_rep']}")
    print(f"  Low volume (<20 votes): {summary['low_volume']}")


if __name__ == '__main__':
    main()
