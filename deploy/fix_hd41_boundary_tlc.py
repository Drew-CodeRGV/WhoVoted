#!/usr/bin/env python3
"""
Fix HD-41 boundary using the OFFICIAL Texas Legislative Council shapefile (PLANH2316).

Downloads from: https://data.capitol.texas.gov/dataset/planh2316
File: PLANH2316.zip (shapefile)

This is the AUTHORITATIVE source for Texas House district boundaries (2023-2026).
"""
import json, urllib.request, zipfile, io, os, sys, subprocess, tempfile
from pathlib import Path

DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
BOUNDARY_CACHE = '/opt/whovoted/public/cache/hd41_boundary.json'
SHAPEFILE_URL = 'https://data.capitol.texas.gov/dataset/e0635274-3fba-4ace-8192-e4e67a0a7951/resource/3f3e52e5-a4f0-4b5e-a968-e1b1d2a8e7a0/download/planh2316.zip'
# Fallback URL pattern
SHAPEFILE_URL_ALT = 'https://data.capitol.texas.gov/dataset/planh2316/resource/planh2316-zip'


def reproject_geometry(geom, prj_path):
    """Reproject geometry from projected CRS to WGS84 (EPSG:4326) using pyproj."""
    try:
        from pyproj import Transformer, CRS
        # Read the .prj file to determine source CRS
        with open(prj_path) as f:
            prj_wkt = f.read()
        src_crs = CRS.from_wkt(prj_wkt)
        transformer = Transformer.from_crs(src_crs, CRS.from_epsg(4326), always_xy=True)

        def transform_coords(coords):
            return [list(transformer.transform(x, y)) for x, y in coords]

        if geom['type'] == 'Polygon':
            new_coords = [transform_coords(ring) for ring in geom['coordinates']]
            return {'type': 'Polygon', 'coordinates': new_coords}
        elif geom['type'] == 'MultiPolygon':
            new_coords = [[transform_coords(ring) for ring in poly] for poly in geom['coordinates']]
            return {'type': 'MultiPolygon', 'coordinates': new_coords}
        return geom
    except ImportError:
        print("  WARNING: pyproj not installed. Trying manual Texas State Plane conversion...")
        # Texas State Plane South Central (EPSG:2278) approximate conversion
        # This is a rough approximation — good enough for display
        # For Texas South zone: origin lat ~25.67, central meridian ~-98.5
        import math
        def sp_to_latlon(x, y):
            # Approximate inverse for Texas State Plane South Central (feet)
            # These are rough constants for the Hidalgo County area
            # More accurate: use pyproj
            lat = 25.6667 + (y - 0) / 364567.0  # ~364567 ft per degree lat
            lng = -98.5 + (x - 0) / (364567.0 * math.cos(math.radians(26.2)))  # adjusted for latitude
            return [lng, lat]

        # Actually for meters (not feet), the TLC uses NAD83 Texas State Plane South Central (meters)
        # EPSG:32140 or similar
        def meters_to_latlon(x, y):
            # Very rough: 1 degree lat ≈ 111,000m, 1 degree lng ≈ 99,000m at lat 26
            lat = 25.0 + y / 111000.0
            lng = -100.0 + x / 99000.0
            return [lng, lat]

        def transform_coords(coords):
            return [meters_to_latlon(x, y) for x, y in coords]

        if geom['type'] == 'Polygon':
            return {'type': 'Polygon', 'coordinates': [transform_coords(ring) for ring in geom['coordinates']]}
        elif geom['type'] == 'MultiPolygon':
            return {'type': 'MultiPolygon', 'coordinates': [[transform_coords(ring) for ring in poly] for poly in geom['coordinates']]}
        return geom


def download_shapefile():
    """Download PLANH2316 shapefile."""
    # Try to find the actual download URL
    # First try the dataset page to get resource links
    try:
        print("  Fetching dataset page for download URL...")
        req = urllib.request.Request(
            'https://data.capitol.texas.gov/api/3/action/package_show?id=planh2316',
            headers={'User-Agent': 'WhoVoted/1.0'}
        )
        resp = urllib.request.urlopen(req, timeout=30)
        data = json.loads(resp.read())
        resources = data.get('result', {}).get('resources', [])
        # Find the shapefile resource
        shp_url = None
        for r in resources:
            name = (r.get('name', '') + r.get('description', '')).lower()
            fmt = r.get('format', '').lower()
            if 'shapefile' in name or (fmt == 'zip' and 'shp' in name) or r.get('name') == 'PLANH2316.zip':
                shp_url = r.get('url')
                break
            # Also try the first zip that's just the plan name
            if r.get('name', '').startswith('PLANH2316') and r.get('format', '').upper() == 'ZIP' and 'blk' not in r.get('name', '').lower() and 'kml' not in r.get('name', '').lower() and 'All_Files' not in r.get('name', ''):
                shp_url = r.get('url')
                break
        if shp_url:
            print(f"  Found shapefile URL: {shp_url[:80]}...")
        else:
            print("  Could not find shapefile URL in API response")
            print(f"  Resources: {[r.get('name') for r in resources[:10]]}")
            return None
    except Exception as e:
        print(f"  API failed: {e}")
        shp_url = SHAPEFILE_URL  # try hardcoded URL

    # Download
    print(f"  Downloading shapefile...")
    try:
        req = urllib.request.Request(shp_url, headers={'User-Agent': 'WhoVoted/1.0'})
        resp = urllib.request.urlopen(req, timeout=120)
        zip_data = resp.read()
        print(f"  Downloaded {len(zip_data)/1024:.0f} KB")
        return zip_data
    except Exception as e:
        print(f"  Download failed: {e}")
        return None


def extract_hd41(zip_data):
    """Extract HD-41 from the shapefile using Python (no ogr2ogr needed)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Extract zip
        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            zf.extractall(tmpdir)

        # Find .shp file
        shp_files = []
        for root, dirs, files in os.walk(tmpdir):
            for f in files:
                if f.endswith('.shp'):
                    shp_files.append(os.path.join(root, f))

        if not shp_files:
            print("  ERROR: No .shp file found in zip")
            return None

        shp_path = shp_files[0]
        print(f"  Found shapefile: {Path(shp_path).name}")

        # Try fiona first
        try:
            import fiona
            from shapely.geometry import shape, mapping
            print("  Using fiona to read shapefile...")
            with fiona.open(shp_path) as src:
                print(f"  Schema fields: {list(src.schema['properties'].keys())}")
                for feat in src:
                    props = dict(feat['properties'])
                    # Check various field names for district 41
                    for field in ['DISTRICT', 'District', 'district', 'SLDL', 'NAME', 'BASENAME', 'DIST_NUM']:
                        val = str(props.get(field, ''))
                        if val == '41' or val == '041' or val == 'District 41' or val == 'State House District 41':
                            print(f"  ✓ Found HD-41 via {field}={val}")
                            geom = mapping(shape(feat['geometry']))
                            return {'type': 'Feature', 'properties': props, 'geometry': geom}
                # If not found, print sample
                src.seek(0)
                sample = next(iter(src))
                print(f"  Sample props: {dict(sample['properties'])}")
            return None
        except ImportError:
            pass

        # Try pyshp (shapefile) library
        try:
            import shapefile
            print("  Using pyshp to read shapefile...")
            sf = shapefile.Reader(shp_path)
            fields = [f[0] for f in sf.fields[1:]]
            print(f"  Fields: {fields}")

            # Check if we need to reproject (read .prj file)
            prj_path = shp_path.replace('.shp', '.prj')
            needs_reproject = False
            if os.path.exists(prj_path):
                with open(prj_path) as pf:
                    prj_text = pf.read()
                if 'GEOGCS' not in prj_text or 'PROJCS' in prj_text:
                    needs_reproject = True
                    print(f"  Shapefile is in projected CRS — will reproject to WGS84")

            for rec in sf.iterShapeRecords():
                props = dict(zip(fields, rec.record))
                for field in ['DISTRICT', 'District', 'district', 'SLDL', 'NAME', 'BASENAME', 'DIST_NUM']:
                    val = str(props.get(field, ''))
                    if val == '41' or val == '041':
                        print(f"  ✓ Found HD-41 via {field}={val}")
                        geom = rec.shape.__geo_interface__

                        if needs_reproject:
                            geom = reproject_geometry(geom, prj_path)

                        return {'type': 'Feature', 'properties': {k: str(v) for k, v in props.items()}, 'geometry': geom}
            # Print sample
            sample = next(sf.iterShapeRecords())
            print(f"  Sample: {dict(zip(fields, sample.record))}")
            return None
        except ImportError:
            pass

        # Last resort: try ogr2ogr
        print("  Neither fiona nor pyshp available. Trying ogr2ogr...")
        geojson_path = os.path.join(tmpdir, 'hd41.geojson')
        for field_filter in ["DISTRICT='41'", "DISTRICT=41"]:
            result = subprocess.run(
                ['ogr2ogr', '-f', 'GeoJSON', '-where', field_filter, geojson_path, shp_path],
                capture_output=True, text=True
            )
            if result.returncode == 0 and os.path.exists(geojson_path) and os.path.getsize(geojson_path) > 100:
                with open(geojson_path) as f:
                    data = json.load(f)
                if data.get('features'):
                    return data['features'][0]
            if os.path.exists(geojson_path):
                os.remove(geojson_path)

        print("  ERROR: No shapefile reader available. Install: pip install pyshp")
        return None


def validate_and_save(feature):
    """Validate and save the new boundary."""
    geom = feature['geometry']
    if geom['type'] == 'Polygon':
        coords = geom['coordinates'][0]
    elif geom['type'] == 'MultiPolygon':
        coords = geom['coordinates'][0][0]
    else:
        print(f"  ERROR: Unexpected geometry type: {geom['type']}")
        return False

    lngs = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    center_lat = (min(lats) + max(lats)) / 2
    center_lng = (min(lngs) + max(lngs)) / 2

    print(f"  New boundary: {len(coords)} vertices")
    print(f"  Center: {center_lat:.4f}, {center_lng:.4f}")
    print(f"  Bbox: lat {min(lats):.4f}-{max(lats):.4f}, lng {min(lngs):.4f}-{max(lngs):.4f}")

    # Validate it's in the right area
    if not (25.8 < center_lat < 26.6 and -98.6 < center_lng < -97.8):
        print("  ERROR: Boundary not in expected Hidalgo County area")
        return False

    # Update districts.json
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)
    districts['features'] = [f for f in districts['features'] if f.get('properties', {}).get('district_id') != 'HD-41']

    new_feature = {
        'type': 'Feature',
        'properties': {
            'district_type': 'state_house',
            'district_id': 'HD-41',
            'district_name': 'TX State House District 41 (PLANH2316)',
            'NAME': 'State House District 41',
            'BASENAME': '41',
            'SLDL': '041',
            'STATE': '48',
            'LSY': '2022',
            'source': 'Texas Legislative Council PLANH2316',
            'color': '#FF6347',
        },
        'geometry': feature['geometry']
    }
    districts['features'].append(new_feature)

    with open(DISTRICTS_PATH, 'w') as f:
        json.dump(districts, f)
    print(f"  ✓ Updated districts.json")

    # Update boundary cache
    with open(BOUNDARY_CACHE, 'w') as f:
        json.dump({'type': 'FeatureCollection', 'features': [new_feature]}, f, separators=(',', ':'))
    print(f"  ✓ Updated hd41_boundary.json ({Path(BOUNDARY_CACHE).stat().st_size/1024:.0f} KB)")

    return True


def main():
    print("Fixing HD-41 boundary from Texas Legislative Council (PLANH2316)...\n")

    zip_data = download_shapefile()
    if not zip_data:
        sys.exit(1)

    feature = extract_hd41(zip_data)
    if not feature:
        sys.exit(1)

    print("\nValidating and saving...")
    if not validate_and_save(feature):
        sys.exit(1)

    print("\n✓ HD-41 boundary updated from PLANH2316 (official TLC source)")
    print("  Next steps:")
    print("  1. python3 deploy/add_hd41_boundary.py  (re-assign voters)")
    print("  2. python3 deploy/cache_hd41_precincts_verified.py  (rebuild caches)")


if __name__ == '__main__':
    main()
