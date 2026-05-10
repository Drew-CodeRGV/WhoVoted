#!/usr/bin/env python3
"""
Extract precinct boundary polygons for HD-41 from ALL available boundary files.
Tries both Hidalgo and Cameron county boundary files.
"""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
BOUNDARY_FILES = [
    '/opt/whovoted/public/data/precinct_boundaries.json',
    '/opt/whovoted/public/data/precinct_boundaries_cameron.json',
    '/opt/whovoted/public/data/precinct_boundaries_combined.json',
]
CACHE_PATH = '/opt/whovoted/public/cache/hd41_precinct_shapes.json'

def normalize_precinct(pct_str):
    """Normalize precinct string for matching."""
    s = pct_str.replace('Precinct ', '').strip()
    # Try to get numeric value
    try:
        return str(int(s))
    except ValueError:
        return s.lstrip('0') or '0'

def main():
    print("Building HD-41 precinct shapes (v2 — all boundary files)...")

    conn = sqlite3.connect(DB_PATH)
    hd41_precincts = set(r[0] for r in conn.execute("""
        SELECT DISTINCT precinct FROM voters
        WHERE state_house_district = 'HD-41' AND precinct IS NOT NULL
    """).fetchall())
    print(f"  HD-41 has {len(hd41_precincts)} precincts in DB")

    # Build normalized lookup
    db_pct_normalized = {}
    for pct in hd41_precincts:
        norm = normalize_precinct(pct)
        db_pct_normalized[norm] = pct
        db_pct_normalized[pct] = pct  # also keep original
    conn.close()

    matched = {}  # db_precinct -> feature

    for path in BOUNDARY_FILES:
        if not Path(path).exists():
            continue
        print(f"  Loading {Path(path).name}...")
        with open(path) as f:
            data = json.load(f)
        features = data.get('features', []) if isinstance(data, dict) else data

        # Find precinct field
        if features:
            props = features[0].get('properties', {})
            precinct_field = None
            for field in ['precinct', 'PRECINCT', 'Precinct', 'PCT', 'NAME', 'name', 'VTDST', 'precinct_id']:
                if field in props:
                    precinct_field = field
                    break
            if not precinct_field:
                precinct_field = list(props.keys())[0] if props else None
            print(f"    Field: {precinct_field}, features: {len(features)}")

        for feature in features:
            props = feature.get('properties', {})
            pct_value = str(props.get(precinct_field, '')).strip()
            norm = normalize_precinct(pct_value)

            if norm in db_pct_normalized and db_pct_normalized[norm] not in matched:
                db_pct = db_pct_normalized[norm]
                feature['properties']['db_precinct'] = db_pct
                matched[db_pct] = feature

    print(f"\n  Total matched: {len(matched)} precinct boundaries")
    print(f"  Unmatched: {len(hd41_precincts) - len(matched)}")

    if matched:
        output = {'type': 'FeatureCollection', 'features': list(matched.values())}
        Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_PATH, 'w') as f:
            json.dump(output, f, separators=(',', ':'))
        print(f"✓ Saved {len(matched)} precinct shapes ({Path(CACHE_PATH).stat().st_size/1024:.0f} KB)")
    else:
        print("ERROR: No matches found")

if __name__ == '__main__':
    main()
