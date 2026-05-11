#!/usr/bin/env python3
"""
Build the FINAL HD-41 precinct map using:
1. Official canvass precincts (66 precincts — these ARE HD-41 by definition)
2. VTD boundary polygons from TLC
3. Real candidate-level vote data from the canvass

No geometric filtering — if the county reported it under HD-41, it's in HD-41.
Include ALL 66 precincts. Match each to its VTD boundary.
For the 2 edge cases where centroid is barely outside the TLC polygon, include anyway.
"""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
VTD_PATH = '/opt/whovoted/public/data/hidalgo_vtd_boundaries.json'
SHAPES_OUT = '/opt/whovoted/public/cache/hd41_precinct_shapes.json'
RESULTS_OUT = '/opt/whovoted/public/cache/hd41_precinct_results.json'
PLANNER_OUT = '/opt/whovoted/public/cache/hd41_planner.json'

ELECTION_DATE = '2026-03-03'


def main():
    print("Building FINAL HD-41 dataset — all 66 official canvass precincts...\n")

    # Load VTD boundaries
    with open(VTD_PATH) as f:
        vtd_data = json.load(f)

    # Build VTD lookup by normalized ID
    vtd_lookup = {}
    for feat in vtd_data['features']:
        vtd_id = feat['properties'].get('vtd_id', feat['properties'].get('VTD', ''))
        # Store by multiple keys
        vtd_lookup[vtd_id] = feat
        vtd_lookup[vtd_id.lstrip('0') or '0'] = feat
        vtd_lookup[vtd_id.zfill(3)] = feat
        vtd_lookup[vtd_id.zfill(4)] = feat

    # Get official canvass data from DB
    conn = sqlite3.connect(DB_PATH)

    # All canvass precincts and their candidate results
    canvass_rows = conn.execute("""
        SELECT precinct, party, candidate, votes
        FROM hd41_candidate_results
        WHERE election_date = '2026-03-03'
        ORDER BY precinct, party, candidate
    """).fetchall()

    # Aggregate by precinct
    precincts = {}
    for pct, party, candidate, votes in canvass_rows:
        if pct not in precincts:
            precincts[pct] = {'dem_candidates': {}, 'rep_candidates': {}, 'dem_total': 0, 'rep_total': 0}
        if party == 'Democratic':
            precincts[pct]['dem_candidates'][candidate] = votes
            precincts[pct]['dem_total'] += votes
        elif party == 'Republican':
            precincts[pct]['rep_candidates'][candidate] = votes
            precincts[pct]['rep_total'] += votes

    print(f"  Official canvass precincts: {len(precincts)}")

    # Get registered voter counts and centroids from voter rolls
    reg_data = {}
    for pct, cnt, lat, lng in conn.execute("""
        SELECT precinct, COUNT(*), AVG(lat), AVG(lng)
        FROM voters
        WHERE state_house_district = 'HD-41' AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """).fetchall():
        # Normalize to match canvass format (3-digit zero-padded)
        norm = pct.lstrip('0') or '0'
        if '.' in pct:
            norm = pct.split('.')[0].lstrip('0') or '0'
        key = norm.zfill(3)
        if key not in reg_data:
            reg_data[key] = {'registered': 0, 'lat': lat, 'lng': lng}
        reg_data[key]['registered'] += cnt

    # Also try direct match
    for pct, cnt, lat, lng in conn.execute("""
        SELECT precinct, COUNT(*), AVG(lat), AVG(lng)
        FROM voters
        WHERE state_house_district = 'HD-41' AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """).fetchall():
        if pct in precincts and pct not in reg_data:
            reg_data[pct] = {'registered': cnt, 'lat': lat, 'lng': lng}

    conn.close()

    # Build results for each canvass precinct
    shapes = []
    results = []

    for pct, data in sorted(precincts.items()):
        dem = data['dem_total']
        rep = data['rep_total']
        total = dem + rep
        if total == 0:
            continue

        # Get registered voters
        reg_info = reg_data.get(pct, reg_data.get(pct.zfill(3), reg_data.get(pct.lstrip('0'), {})))
        registered = reg_info.get('registered', 0)
        lat = reg_info.get('lat')
        lng = reg_info.get('lng')

        # Winner
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

        # Dem race winner in this precinct
        dem_winner = max(data['dem_candidates'].items(), key=lambda x: x[1])[0] if data['dem_candidates'] else None
        rep_winner = max(data['rep_candidates'].items(), key=lambda x: x[1])[0] if data['rep_candidates'] else None

        result = {
            'precinct': pct,
            'lat': round(lat, 4) if lat else None,
            'lng': round(lng, 4) if lng else None,
            'registered': registered,
            'dem_votes': dem,
            'rep_votes': rep,
            'total_votes': total,
            'winner': winner,
            'margin_votes': margin_votes,
            'margin_pct': margin_pct,
            'turnout_pct': round(total / registered * 100, 1) if registered > 0 else 0,
            'dem_share': round(dem / total * 100, 1),
            'rep_share': round(rep / total * 100, 1),
            'dem_candidates': data['dem_candidates'],
            'rep_candidates': data['rep_candidates'],
            'dem_winner': dem_winner,
            'rep_winner': rep_winner,
        }
        results.append(result)

        # Find VTD boundary
        vtd_feat = vtd_lookup.get(pct) or vtd_lookup.get(pct.zfill(4)) or vtd_lookup.get(pct.lstrip('0'))
        if vtd_feat:
            shape = {
                'type': 'Feature',
                'properties': {
                    'db_precinct': pct,
                    'dem': dem, 'rep': rep, 'total': total,
                    'winner': winner, 'margin_pct': margin_pct,
                    'dem_winner': dem_winner, 'rep_winner': rep_winner,
                },
                'geometry': vtd_feat['geometry']
            }
            shapes.append(shape)

    print(f"  Results: {len(results)} precincts with vote data")
    print(f"  Shapes: {len(shapes)} precincts with VTD boundaries")

    # Summary
    total_dem = sum(r['dem_votes'] for r in results)
    total_rep = sum(r['rep_votes'] for r in results)
    total_votes = total_dem + total_rep

    # Planner
    planner_items = []
    for r in results:
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
        })
    planner_items.sort(key=lambda x: x['priority_score'], reverse=True)

    summary = {
        'total_precincts': len(results),
        'precincts_with_shapes': len(shapes),
        'total_dem_votes': total_dem,
        'total_rep_votes': total_rep,
        'total_votes': total_votes,
        'battleground': len([p for p in planner_items if p['classification'] == 'Battleground']),
        'dem_strongholds': len([p for p in planner_items if p['classification'] == 'Dem Stronghold']),
        'rep_strongholds': len([p for p in planner_items if p['classification'] == 'Rep Stronghold']),
        'lean_dem': len([p for p in planner_items if p['classification'] == 'Lean Dem']),
        'lean_rep': len([p for p in planner_items if p['classification'] == 'Lean Rep']),
        'low_volume': len([p for p in planner_items if p['classification'] == 'Low Volume']),
        'data_source': 'Hidalgo County Official Canvass (precinct-by-precinct)',
        'election_date': ELECTION_DATE,
    }

    # Write
    Path(SHAPES_OUT).parent.mkdir(parents=True, exist_ok=True)
    with open(SHAPES_OUT, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': shapes}, f, separators=(',', ':'))
    with open(RESULTS_OUT, 'w') as f:
        json.dump({'election_date': ELECTION_DATE, 'district': 'HD-41', 'summary': summary, 'precincts': results}, f, separators=(',', ':'))
    with open(PLANNER_OUT, 'w') as f:
        json.dump({'district': 'HD-41', 'summary': summary, 'top_priority': planner_items[:30], 'all_precincts': planner_items}, f, separators=(',', ':'))

    print(f"\n{'='*60}")
    print(f"  ✓ Shapes: {Path(SHAPES_OUT).stat().st_size/1024:.0f} KB ({len(shapes)} precincts)")
    print(f"  ✓ Results: {Path(RESULTS_OUT).stat().st_size/1024:.0f} KB ({len(results)} precincts)")
    print(f"  ✓ Planner: {Path(PLANNER_OUT).stat().st_size/1024:.0f} KB")
    print(f"\n  Total: {total_votes:,} votes (D:{total_dem:,} R:{total_rep:,})")
    print(f"  Coverage: {len(shapes)}/{len(results)} precincts have boundary outlines")
    print(f"  Battleground: {summary['battleground']} | Dem strongholds: {summary['dem_strongholds']}")
    print(f"  Lean Dem: {summary['lean_dem']} | Rep strongholds: {summary['rep_strongholds']} | Lean Rep: {summary['lean_rep']}")


if __name__ == '__main__':
    main()
