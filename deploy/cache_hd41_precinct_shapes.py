#!/usr/bin/env python3
"""
Extract precinct boundary polygons for HD-41 precincts and save as a GeoJSON
file that the frontend can load and color by candidate performance.
"""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
PRECINCT_BOUNDARIES = '/opt/whovoted/public/data/precinct_boundaries.json'
PRECINCT_COMBINED = '/opt/whovoted/public/data/precinct_boundaries_combined.json'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_precinct_shapes.json'

def main():
    print("Building HD-41 precinct shapes...")

    # Get list of precincts in HD-41
    conn = sqlite3.connect(DB_PATH)
    hd41_precincts = set(r[0] for r in conn.execute("""
        SELECT DISTINCT precinct FROM voters
        WHERE state_house_district = 'HD-41' AND precinct IS NOT NULL
    """).fetchall())
    print(f"  HD-41 has {len(hd41_precincts)} precincts in DB")
    conn.close()

    # Try loading precinct boundaries
    boundaries = None
    for path in [PRECINCT_BOUNDARIES, PRECINCT_COMBINED]:
        if Path(path).exists():
            print(f"  Loading {path}...")
            with open(path) as f:
                data = json.load(f)
            if isinstance(data, dict) and 'features' in data:
                boundaries = data
                break
            elif isinstance(data, list):
                boundaries = {'type': 'FeatureCollection', 'features': data}
                break

    if not boundaries:
        print("ERROR: No precinct boundary file found")
        return

    print(f"  Boundary file has {len(boundaries['features'])} features")

    # Inspect first feature to understand property names
    if boundaries['features']:
        props = boundaries['features'][0].get('properties', {})
        print(f"  Sample properties: {list(props.keys())[:10]}")
        # Try to find the precinct identifier field
        precinct_field = None
        for field in ['PRECINCT', 'precinct', 'Precinct', 'PCT', 'pct', 'Pct',
                      'PREC', 'prec', 'NAME', 'name', 'Name', 'VTDST', 'VTD',
                      'PRECINCTID', 'PrecinctID', 'PCTNUM', 'PCT_NUM']:
            if field in props:
                precinct_field = field
                break
        if not precinct_field:
            # Try first string field
            for k, v in props.items():
                if isinstance(v, str) and v.strip():
                    precinct_field = k
                    break
        print(f"  Using precinct field: {precinct_field}")
        print(f"  Sample values: {[f['properties'].get(precinct_field) for f in boundaries['features'][:5]]}")

    # Filter to HD-41 precincts
    matched = []
    for feature in boundaries['features']:
        props = feature.get('properties', {})
        pct_value = str(props.get(precinct_field, '')).strip()

        # Boundary format: "Precinct 0081" → extract numeric part
        # DB format: "081", "81", "0372", "7.01", "S 2066", etc.
        boundary_num = pct_value.replace('Precinct ', '').strip()
        boundary_num_stripped = boundary_num.lstrip('0') or '0'

        matched_pct = None
        for db_pct in hd41_precincts:
            db_stripped = db_pct.lstrip('0') or '0'
            # Direct match
            if db_pct == boundary_num or db_stripped == boundary_num_stripped:
                matched_pct = db_pct
                break
            # Zero-padded match: DB "081" == boundary "0081"
            if db_pct.zfill(4) == boundary_num.zfill(4):
                matched_pct = db_pct
                break
            # Numeric match for simple numbers
            try:
                if int(db_pct) == int(boundary_num):
                    matched_pct = db_pct
                    break
            except (ValueError, TypeError):
                pass

        if matched_pct:
            feature['properties']['db_precinct'] = matched_pct
            matched.append(feature)

    print(f"  Matched {len(matched)} precinct boundaries to HD-41")
    print(f"  Unmatched HD-41 precincts (no boundary): {len(hd41_precincts) - len(set(f['properties']['db_precinct'] for f in matched))}")

    if not matched:
        print("\n  WARNING: No matches found. Checking precinct format mismatch...")
        boundary_pcts = set(str(f['properties'].get(precinct_field, '')).strip() for f in boundaries['features'])
        print(f"  Boundary precinct samples: {list(boundary_pcts)[:20]}")
        print(f"  DB precinct samples: {list(hd41_precincts)[:20]}")
        return

    # Write output
    output = {
        'type': 'FeatureCollection',
        'features': matched
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    print(f"\n✓ Saved {len(matched)} precinct shapes to {CACHE_PATH}")
    print(f"  File size: {Path(CACHE_PATH).stat().st_size / 1024:.0f} KB")

if __name__ == '__main__':
    main()
