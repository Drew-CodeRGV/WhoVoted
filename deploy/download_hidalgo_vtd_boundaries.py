#!/usr/bin/env python3
"""
Download Hidalgo County VTD (Voting Tabulation District) boundaries from Census TIGER/Line.

This gives us polygon outlines for EVERY precinct in Hidalgo County (FIPS 48215).
The file is tl_2024_48_vtd20.zip — all Texas VTDs from the 2020 Census.

We filter to Hidalgo County (COUNTYFP20='215') and save as GeoJSON.
Then we match these to our DB precincts and rebuild the HD-41 precinct shapes.
"""
import json, urllib.request, zipfile, io, os, tempfile, sqlite3
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
VTD_OUTPUT = '/opt/whovoted/public/data/hidalgo_vtd_boundaries.json'
HD41_SHAPES_OUTPUT = '/opt/whovoted/public/cache/hd41_precinct_shapes.json'

# Texas Legislative Council VTD files — the AUTHORITATIVE source
# These are the actual precinct boundaries used in elections
VTD_URLS = [
    # 2024 Primary & General VTDs from TLC (best match for 2026 primary)
    'https://data.capitol.texas.gov/dataset/3e16afb0-ba6c-4e36-8b5e-4e3e92f0c9a5/resource/vtds-24pg-zip/download/vtds_24pg.zip',
]

# Also try the CKAN API to find the actual download URL
TLC_DATASET_API = 'https://data.capitol.texas.gov/api/3/action/package_show?id=vtds'

# Hidalgo County FIPS = 215
HIDALGO_FIPS = '215'


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


def download_vtd():
    """Download the Texas VTD shapefile from TLC."""
    # First try the CKAN API to get the real download URL
    try:
        print("Fetching VTD download URL from TLC API...")
        req = urllib.request.Request(TLC_DATASET_API, headers={'User-Agent': 'WhoVoted/1.0'})
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        resources = data.get('result', {}).get('resources', [])
        for r in resources:
            name = r.get('name', '').lower()
            if 'vtds_24pg' in name and r.get('format', '').upper() == 'ZIP':
                url = r.get('url')
                print(f"  Found: {r.get('name')} -> {url[:80]}...")
                VTD_URLS.insert(0, url)
                break
            elif '24pg' in name and '.zip' in name.lower():
                url = r.get('url')
                print(f"  Found: {r.get('name')} -> {url[:80]}...")
                VTD_URLS.insert(0, url)
                break
    except Exception as e:
        print(f"  API lookup failed: {e}")

    for url in VTD_URLS:
        print(f"Trying {url[:80]}...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'WhoVoted/1.0'})
            resp = urllib.request.urlopen(req, timeout=300)
            data = resp.read()
            print(f"  ✓ Downloaded {len(data)/1024/1024:.1f} MB")
            return data
        except Exception as e:
            print(f"  Failed: {e}")
    print("ERROR: Could not download VTD file")
    return None


def extract_hidalgo_vtds(zip_data):
    """Extract Hidalgo County VTDs from the shapefile."""
    import shapefile as shp

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            zf.extractall(tmpdir)

        # Find .shp
        shp_path = None
        for root, dirs, files in os.walk(tmpdir):
            for f in files:
                if f.endswith('.shp'):
                    shp_path = os.path.join(root, f)
                    break

        if not shp_path:
            print("  ERROR: No .shp file found")
            return None

        # Check if needs reprojection
        prj_path = shp_path.replace('.shp', '.prj')
        needs_reproject = False
        if os.path.exists(prj_path):
            with open(prj_path) as pf:
                prj_text = pf.read()
            if 'PROJCS' in prj_text:
                needs_reproject = True
                print(f"  Shapefile is projected — will reproject to WGS84")

        transformer = None
        if needs_reproject:
            try:
                from pyproj import Transformer, CRS
                src_crs = CRS.from_wkt(open(prj_path).read())
                transformer = Transformer.from_crs(src_crs, CRS.from_epsg(4326), always_xy=True)
            except Exception as e:
                print(f"  WARNING: pyproj reproject failed: {e}")

        print(f"  Reading {Path(shp_path).name}...")
        sf = shp.Reader(shp_path)
        fields = [f[0] for f in sf.fields[1:]]
        print(f"  Fields: {fields}")

        # Determine county field and VTD field
        # TLC uses: CNTY (county FIPS as number), VTD (name), CNTYVTD (unique key)
        # Census uses: COUNTYFP20, VTDST20, NAME20
        county_field = None
        vtd_field = None
        for f in fields:
            if f.upper() in ('CNTY', 'COUNTYFP20', 'COUNTYFP', 'COUNTY'):
                county_field = f
            if f.upper() in ('VTD', 'VTDST20', 'VTDST', 'NAME20', 'NAME'):
                vtd_field = f
        print(f"  County field: {county_field}, VTD field: {vtd_field}")

        # Hidalgo County FIPS = 215
        hidalgo_values = ['215', 215, '0215']

        hidalgo_features = []
        total = 0
        for rec in sf.iterShapeRecords():
            total += 1
            props = dict(zip(fields, rec.record))
            county_val = props.get(county_field)
            # Check if Hidalgo
            if str(county_val).strip() not in ['215', '0215'] and county_val != 215:
                continue

            geom = rec.shape.__geo_interface__

            # Reproject if needed
            if transformer and geom.get('coordinates'):
                def transform_ring(ring):
                    return [list(transformer.transform(x, y)) for x, y in ring]
                if geom['type'] == 'Polygon':
                    geom['coordinates'] = [transform_ring(ring) for ring in geom['coordinates']]
                elif geom['type'] == 'MultiPolygon':
                    geom['coordinates'] = [[transform_ring(ring) for ring in poly] for poly in geom['coordinates']]

            vtd_name = str(props.get(vtd_field, '')).strip()
            hidalgo_features.append({
                'type': 'Feature',
                'properties': {
                    'vtd_id': vtd_name,
                    'vtd_name': vtd_name,
                    'county_fips': '215',
                    **{k: str(v).strip() for k, v in props.items()}
                },
                'geometry': geom
            })

        print(f"  Total VTDs in file: {total}")
        print(f"  Hidalgo County VTDs: {len(hidalgo_features)}")
        if hidalgo_features:
            sample = hidalgo_features[0]['properties']
            print(f"  Sample: vtd_id={sample.get('vtd_id')}, fields={list(sample.keys())[:6]}")
            # Print a few VTD names
            names = [f['properties']['vtd_id'] for f in hidalgo_features[:10]]
            print(f"  First 10 VTD names: {names}")

        return hidalgo_features


def save_hidalgo_vtds(features):
    """Save Hidalgo VTDs as GeoJSON."""
    output = {'type': 'FeatureCollection', 'features': features}
    Path(VTD_OUTPUT).parent.mkdir(parents=True, exist_ok=True)
    with open(VTD_OUTPUT, 'w') as f:
        json.dump(output, f, separators=(',', ':'))
    print(f"  ✓ Saved {len(features)} VTDs to {VTD_OUTPUT} ({Path(VTD_OUTPUT).stat().st_size/1024:.0f} KB)")


def match_vtds_to_hd41(features):
    """Match VTD boundaries to HD-41 precincts using geometric intersection."""
    print("\nMatching VTDs to HD-41 precincts...")

    # Load HD-41 boundary
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)
    hd41 = next((feat for feat in districts['features']
                 if feat.get('properties', {}).get('district_id') == 'HD-41'), None)
    if not hd41:
        print("  ERROR: HD-41 not found in districts.json")
        return

    hd41_geom = hd41['geometry']

    # Load DB precincts
    conn = sqlite3.connect(DB_PATH)
    db_precincts = set(r[0] for r in conn.execute("""
        SELECT DISTINCT precinct FROM voters
        WHERE state_house_district='HD-41' AND precinct IS NOT NULL
    """).fetchall())
    # Also get centroids
    centroids = {}
    for pct, lat, lng in conn.execute("""
        SELECT precinct, AVG(lat), AVG(lng) FROM voters
        WHERE state_house_district='HD-41' AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """).fetchall():
        centroids[pct] = (lat, lng)
    conn.close()

    print(f"  DB has {len(db_precincts)} HD-41 precincts")
    print(f"  VTD file has {len(features)} Hidalgo County VTDs")

    # Build VTD lookup by various ID formats
    vtd_lookup = {}
    for feat in features:
        props = feat['properties']
        vtd_id = props.get('vtd_id', '')
        vtd_name = props.get('vtd_name', '')
        # Store by multiple keys for matching
        vtd_lookup[vtd_id] = feat
        vtd_lookup[vtd_name] = feat
        # Numeric stripped version
        try:
            vtd_lookup[str(int(vtd_id))] = feat
        except (ValueError, TypeError):
            pass

    # Match DB precincts to VTDs
    matched = {}
    for db_pct in db_precincts:
        # Try direct match
        if db_pct in vtd_lookup:
            matched[db_pct] = vtd_lookup[db_pct]
            continue
        # Try zero-padded
        try:
            padded = str(int(db_pct)).zfill(4)
            if padded in vtd_lookup:
                matched[db_pct] = vtd_lookup[padded]
                continue
        except (ValueError, TypeError):
            pass
        # Try stripping leading zeros
        stripped = db_pct.lstrip('0') or '0'
        if stripped in vtd_lookup:
            matched[db_pct] = vtd_lookup[stripped]
            continue

    print(f"  Matched by ID: {len(matched)}")

    # For unmatched precincts, try geometric matching:
    # Find the VTD whose centroid is closest to the DB precinct centroid
    unmatched = db_precincts - set(matched.keys())
    if unmatched and centroids:
        print(f"  Trying geometric match for {len(unmatched)} remaining precincts...")
        # Compute VTD centroids
        vtd_centroids = {}
        for feat in features:
            geom = feat['geometry']
            coords = geom['coordinates'][0] if geom['type'] == 'Polygon' else geom['coordinates'][0][0]
            if coords:
                cx = sum(c[0] for c in coords) / len(coords)
                cy = sum(c[1] for c in coords) / len(coords)
                vtd_centroids[id(feat)] = (cy, cx, feat)

        geo_matched = 0
        for db_pct in unmatched:
            if db_pct not in centroids:
                continue
            lat, lng = centroids[db_pct]
            # Find VTD that contains this point
            for feat in features:
                if id(feat) in [id(v) for v in matched.values()]:
                    continue  # already matched
                if point_in_geom(lng, lat, feat['geometry']):
                    matched[db_pct] = feat
                    geo_matched += 1
                    break

        print(f"  Geometric matches: {geo_matched}")

    # Filter to only VTDs inside HD-41 boundary
    verified = {}
    for db_pct, feat in matched.items():
        geom = feat['geometry']
        coords = geom['coordinates'][0] if geom['type'] == 'Polygon' else geom['coordinates'][0][0]
        if not coords:
            continue
        cx = sum(c[0] for c in coords) / len(coords)
        cy = sum(c[1] for c in coords) / len(coords)
        if point_in_geom(cx, cy, hd41_geom):
            feat_copy = dict(feat)
            feat_copy['properties'] = dict(feat['properties'])
            feat_copy['properties']['db_precinct'] = db_pct
            verified[db_pct] = feat_copy

    print(f"  Verified inside HD-41: {len(verified)}")

    # Save
    output = {'type': 'FeatureCollection', 'features': list(verified.values())}
    with open(HD41_SHAPES_OUTPUT, 'w') as f:
        json.dump(output, f, separators=(',', ':'))
    print(f"  ✓ Saved {len(verified)} precinct shapes ({Path(HD41_SHAPES_OUTPUT).stat().st_size/1024:.0f} KB)")


def main():
    # Step 1: Download
    zip_data = download_vtd()

    # Step 2: Extract Hidalgo County
    features = extract_hidalgo_vtds(zip_data)
    if not features:
        return

    # Step 3: Save full Hidalgo VTD file
    save_hidalgo_vtds(features)

    # Step 4: Match to HD-41 and save
    match_vtds_to_hd41(features)

    print("\n✓ Done! Run cache_hd41_precincts_verified.py to rebuild results cache.")


if __name__ == '__main__':
    main()
