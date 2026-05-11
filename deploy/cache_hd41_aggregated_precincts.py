#!/usr/bin/env python3
"""
Build HD-41 precinct map with sub-splits aggregated to parent precincts.

Problem: The DB has 386 precincts with IDs like "081", "081.01", "081.02", "S 2066".
The VTD boundary file has 259 base precincts ("0001" through "0259").
Sub-splits (e.g., "081.01") are subdivisions of parent precinct "081" and share
the same geographic boundary.

Solution: Aggregate all sub-splits to their parent precinct, sum the votes,
and display using the parent's VTD boundary polygon.

This gives us COMPLETE coverage of HD-41 with real, aggregated data.
"""
import sqlite3, json, re
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
VTD_PATH = '/opt/whovoted/public/data/hidalgo_vtd_boundaries.json'
SHAPES_OUT = '/opt/whovoted/public/cache/hd41_precinct_shapes.json'
RESULTS_OUT = '/opt/whovoted/public/cache/hd41_precinct_results.json'
PLANNER_OUT = '/opt/whovoted/public/cache/hd41_planner.json'

ELECTION_DATE = '2026-03-03'
RUNOFF_DATE = '2026-05-26'


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
    if geom['type'] == 'Polygon':
        return point_in_polygon(lng, lat, geom['coordinates'][0])
    elif geom['type'] == 'MultiPolygon':
        return any(point_in_polygon(lng, lat, poly[0]) for poly in geom['coordinates'])
    return False


def get_parent_precinct(pct_id):
    """
    Extract the parent precinct number from a sub-split ID.
    Examples:
      "081" -> "81"
      "081.01" -> "81"
      "7.01" -> "7"
      "S 2066" -> None (special precinct, skip)
      "136" -> "136"
      "0372" -> "372"
      "2051" -> "2051" (could be a valid precinct or a special code)
    """
    s = str(pct_id).strip()

    # Skip special precincts (S prefix, etc.)
    if s.startswith('S ') or s.startswith('s '):
        return None

    # Remove sub-split suffix (everything after the dot)
    if '.' in s:
        s = s.split('.')[0]

    # Strip leading zeros
    s = s.lstrip('0') or '0'

    # Must be numeric
    try:
        int(s)
        return s
    except ValueError:
        return None


def vtd_to_parent(vtd_id):
    """Convert VTD ID (e.g., "0081") to parent precinct number ("81")."""
    s = str(vtd_id).strip().lstrip('0') or '0'
    try:
        int(s)
        return s
    except ValueError:
        return None


def main():
    print("Building HD-41 aggregated precinct data...")
    print("  Aggregating sub-splits to parent precincts for complete coverage.\n")

    # Load HD-41 boundary
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)
    hd41 = next((feat for feat in districts['features']
                 if feat.get('properties', {}).get('district_id') == 'HD-41'), None)
    if not hd41:
        print("ERROR: HD-41 not found in districts.json")
        return
    hd41_geom = hd41['geometry']

    # Load VTD boundaries
    with open(VTD_PATH) as f:
        vtd_data = json.load(f)
    vtd_features = vtd_data.get('features', [])
    print(f"  VTD boundaries: {len(vtd_features)} Hidalgo County precincts")

    # Build VTD lookup: parent_number -> feature
    vtd_by_parent = {}
    for feat in vtd_features:
        vtd_id = feat['properties'].get('vtd_id', feat['properties'].get('VTD', ''))
        parent = vtd_to_parent(vtd_id)
        if parent:
            vtd_by_parent[parent] = feat

    print(f"  VTD parent lookup: {len(vtd_by_parent)} entries")

    # Get all HD-41 voter data from DB
    conn = sqlite3.connect(DB_PATH)

    # All precincts tagged HD-41
    db_precincts = [r[0] for r in conn.execute("""
        SELECT DISTINCT precinct FROM voters
        WHERE state_house_district='HD-41' AND precinct IS NOT NULL
    """).fetchall()]
    print(f"  DB precincts in HD-41: {len(db_precincts)}")

    # Map each DB precinct to its parent
    parent_map = {}  # db_precinct -> parent_number
    orphans = []
    for pct in db_precincts:
        parent = get_parent_precinct(pct)
        if parent:
            parent_map[pct] = parent
        else:
            orphans.append(pct)

    unique_parents = set(parent_map.values())
    print(f"  Mapped to {len(unique_parents)} unique parent precincts")
    print(f"  Orphans (special precincts, skipped): {len(orphans)}")

    # Get real vote data — batch query
    all_votes = conn.execute("""
        SELECT ve.precinct, ve.party_voted, COUNT(*) as cnt
        FROM voter_elections ve
        WHERE ve.election_date=? AND ve.state_house_district='HD-41'
        AND ve.precinct IS NOT NULL
        AND ve.party_voted IN ('Democratic', 'Republican')
        GROUP BY ve.precinct, ve.party_voted
    """, (ELECTION_DATE,)).fetchall()

    # Runoff data
    runoff_votes = conn.execute("""
        SELECT ve.precinct, ve.party_voted, COUNT(*) as cnt
        FROM voter_elections ve
        WHERE ve.election_date=? AND ve.state_house_district='HD-41'
        AND ve.precinct IS NOT NULL
        GROUP BY ve.precinct, ve.party_voted
    """, (RUNOFF_DATE,)).fetchall()

    # Registered voters
    reg_counts = conn.execute("""
        SELECT precinct, COUNT(*) as cnt
        FROM voters WHERE state_house_district='HD-41' AND precinct IS NOT NULL
        GROUP BY precinct
    """).fetchall()

    conn.close()

    # Aggregate to parent precincts
    parent_data = {}  # parent_number -> {dem, rep, reg, runoff_dem, runoff_rep, sub_precincts}

    for pct, party, cnt in all_votes:
        parent = parent_map.get(pct)
        if not parent:
            continue
        if parent not in parent_data:
            parent_data[parent] = {'dem': 0, 'rep': 0, 'reg': 0, 'runoff_dem': 0, 'runoff_rep': 0, 'subs': set()}
        if party == 'Democratic':
            parent_data[parent]['dem'] += cnt
        else:
            parent_data[parent]['rep'] += cnt
        parent_data[parent]['subs'].add(pct)

    for pct, party, cnt in runoff_votes:
        parent = parent_map.get(pct)
        if not parent:
            continue
        if parent not in parent_data:
            parent_data[parent] = {'dem': 0, 'rep': 0, 'reg': 0, 'runoff_dem': 0, 'runoff_rep': 0, 'subs': set()}
        if party == 'Democratic':
            parent_data[parent]['runoff_dem'] += cnt
        elif party == 'Republican':
            parent_data[parent]['runoff_rep'] += cnt

    for pct, cnt in reg_counts:
        parent = parent_map.get(pct)
        if not parent:
            continue
        if parent not in parent_data:
            parent_data[parent] = {'dem': 0, 'rep': 0, 'reg': 0, 'runoff_dem': 0, 'runoff_rep': 0, 'subs': set()}
        parent_data[parent]['reg'] += cnt

    print(f"\n  Parent precincts with vote data: {len(parent_data)}")

    # Match parent precincts to VTD boundaries and verify inside HD-41
    verified_shapes = []
    precinct_results = []
    no_boundary = []

    for parent, data in sorted(parent_data.items(), key=lambda x: x[1]['dem'] + x[1]['rep'], reverse=True):
        dem = data['dem']
        rep = data['rep']
        total = dem + rep
        if total == 0:
            continue

        reg = data['reg']
        runoff_dem = data['runoff_dem']
        runoff_rep = data['runoff_rep']

        # Determine winner
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

        result = {
            'precinct': parent,
            'sub_precincts': sorted(data['subs']),
            'dem_votes': dem,
            'rep_votes': rep,
            'total_votes': total,
            'registered': reg,
            'winner': winner,
            'margin_votes': margin_votes,
            'margin_pct': margin_pct,
            'turnout_pct': round(total / reg * 100, 1) if reg > 0 else 0,
            'dem_share': round(dem / total * 100, 1),
            'rep_share': round(rep / total * 100, 1),
            'runoff_dem': runoff_dem,
            'runoff_rep': runoff_rep,
            'runoff_total': runoff_dem + runoff_rep,
            'has_shape': False,
        }

        # Find VTD boundary
        vtd_feat = vtd_by_parent.get(parent)
        if vtd_feat:
            # Verify centroid is inside HD-41
            geom = vtd_feat['geometry']
            coords = geom['coordinates'][0] if geom['type'] == 'Polygon' else geom['coordinates'][0][0]
            if coords:
                cx = sum(c[0] for c in coords) / len(coords)
                cy = sum(c[1] for c in coords) / len(coords)
                if point_in_geom(cx, cy, hd41_geom):
                    result['has_shape'] = True
                    result['lat'] = round(cy, 4)
                    result['lng'] = round(cx, 4)
                    # Add to shapes
                    shape_feat = {
                        'type': 'Feature',
                        'properties': {
                            'db_precinct': parent,
                            'sub_precincts': sorted(data['subs']),
                            'dem': dem, 'rep': rep, 'total': total,
                        },
                        'geometry': geom
                    }
                    verified_shapes.append(shape_feat)
                else:
                    no_boundary.append(parent)
            else:
                no_boundary.append(parent)
        else:
            no_boundary.append(parent)

        precinct_results.append(result)

    print(f"  Precincts with boundary + data: {len(verified_shapes)}")
    print(f"  Precincts with data but no boundary: {len(no_boundary)}")
    if no_boundary:
        print(f"    Examples: {no_boundary[:10]}")

    # Build priority planner
    planner_items = []
    for r in precinct_results:
        total = r['total_votes']
        margin = abs(r['margin_pct'])
        competitiveness = max(0, 100 - margin)
        priority_score = (competitiveness / 100) * total

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
            'precinct': r['precinct'],
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

    planner_items.sort(key=lambda x: x['priority_score'], reverse=True)

    # Summary
    total_dem = sum(r['dem_votes'] for r in precinct_results)
    total_rep = sum(r['rep_votes'] for r in precinct_results)
    total_votes = total_dem + total_rep

    summary = {
        'total_precincts': len(precinct_results),
        'precincts_with_shapes': len(verified_shapes),
        'precincts_without_shapes': len(no_boundary),
        'battleground': len([p for p in planner_items if p['classification'] == 'Battleground']),
        'dem_strongholds': len([p for p in planner_items if p['classification'] == 'Dem Stronghold']),
        'rep_strongholds': len([p for p in planner_items if p['classification'] == 'Rep Stronghold']),
        'lean_dem': len([p for p in planner_items if p['classification'] == 'Lean Dem']),
        'lean_rep': len([p for p in planner_items if p['classification'] == 'Lean Rep']),
        'low_volume': len([p for p in planner_items if p['classification'] == 'Low Volume']),
        'total_dem_votes': total_dem,
        'total_rep_votes': total_rep,
        'total_votes': total_votes,
        'data_source': 'Hidalgo County voter rolls (voter_elections table)',
        'boundary_source': 'Texas Legislative Council VTDs_24PG (2024 Primary & General)',
        'election_date': ELECTION_DATE,
    }

    # Write outputs
    Path(SHAPES_OUT).parent.mkdir(parents=True, exist_ok=True)

    with open(SHAPES_OUT, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': verified_shapes}, f, separators=(',', ':'))

    with open(RESULTS_OUT, 'w') as f:
        json.dump({'election_date': ELECTION_DATE, 'district': 'HD-41', 'summary': summary,
                   'precincts': precinct_results}, f, separators=(',', ':'))

    with open(PLANNER_OUT, 'w') as f:
        json.dump({'district': 'HD-41', 'summary': summary,
                   'top_battlegrounds': [p for p in planner_items if p['classification'] == 'Battleground'][:20],
                   'top_priority': planner_items[:30],
                   'all_precincts': planner_items}, f, separators=(',', ':'))

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  Shapes: {Path(SHAPES_OUT).stat().st_size/1024:.0f} KB ({len(verified_shapes)} precincts)")
    print(f"  Results: {Path(RESULTS_OUT).stat().st_size/1024:.0f} KB ({len(precinct_results)} precincts)")
    print(f"  Planner: {Path(PLANNER_OUT).stat().st_size/1024:.0f} KB")
    print(f"\n  Total: {total_votes:,} votes (D:{total_dem:,} R:{total_rep:,})")
    print(f"  Battleground: {summary['battleground']}")
    print(f"  Dem strongholds: {summary['dem_strongholds']} | Lean Dem: {summary['lean_dem']}")
    print(f"  Rep strongholds: {summary['rep_strongholds']} | Lean Rep: {summary['lean_rep']}")
    print(f"  Low volume: {summary['low_volume']}")
    print(f"\n  Coverage: {len(verified_shapes)}/{len(precinct_results)} precincts have boundary outlines")


if __name__ == '__main__':
    main()
