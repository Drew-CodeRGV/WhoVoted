#!/usr/bin/env python3
"""
Download HD-41 boundary from Census TIGER/Line and add to districts.json.
Then assign state_house_district='HD-41' to all voters whose precinct centroid
falls within the HD-41 polygon.
"""
import json, sqlite3, urllib.request, zipfile, io, os, sys

DB_PATH = '/opt/whovoted/data/whovoted.db'
DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'

# Census TIGER/Line 2024 State Legislative Districts (Lower Chamber) for Texas
# FIPS state code 48 = Texas
TIGER_URL = 'https://www2.census.gov/geo/tiger/TIGER2024/SLDL/tl_2024_48_sldl.zip'

def download_and_extract_hd41():
    """Download TX state house shapefile and extract HD-41 as GeoJSON."""
    print("Downloading TX state house boundaries from Census TIGER/Line...")
    
    # Try multiple TIGERweb API endpoints
    endpoints = [
        # 2024 TIGER/Line via ArcGIS REST
        'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/18/query?where=STATE%3D%2748%27+AND+BASENAME%3D%2741%27&outFields=*&f=geojson',
        # Alternative layer number
        'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/14/query?where=STATE%3D%2748%27+AND+BASENAME%3D%2741%27&outFields=*&f=geojson',
        'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/16/query?where=STATE%3D%2748%27+AND+BASENAME%3D%2741%27&outFields=*&f=geojson',
        'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/Legislative/MapServer/18/query?where=STATE%3D%2748%27+AND+BASENAME%3D%2741%27&outFields=*&f=geojson',
        # Try SLDL layer
        'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/20/query?where=STATE%3D%2748%27+AND+SLDL%3D%27041%27&outFields=*&f=geojson',
        'https://tigerweb.geo.census.gov/arcgis/rest/services/TIGERweb/tigerWMS_Current/MapServer/22/query?where=STATE%3D%2748%27+AND+SLDL%3D%27041%27&outFields=*&f=geojson',
    ]
    
    for url in endpoints:
        print(f"  Trying: {url[:80]}...")
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'WhoVoted/1.0'})
            resp = urllib.request.urlopen(req, timeout=30)
            data = json.loads(resp.read())
            
            if data.get('features') and len(data['features']) > 0:
                feature = data['features'][0]
                name = feature.get('properties', {}).get('NAME', feature.get('properties', {}).get('BASENAME', 'unknown'))
                print(f"  ✓ Got HD-41: {name}")
                return feature
            elif data.get('error'):
                print(f"    Error: {data['error'].get('message', 'unknown')}")
        except Exception as e:
            print(f"    Failed: {e}")
    
    # Fallback: download the full shapefile zip and extract
    print("\n  All API endpoints failed. Trying shapefile download...")
    try:
        shapefile_url = 'https://www2.census.gov/geo/tiger/TIGER2024/SLDL/tl_2024_48_sldl.zip'
        print(f"  Downloading {shapefile_url}...")
        req = urllib.request.Request(shapefile_url, headers={'User-Agent': 'WhoVoted/1.0'})
        resp = urllib.request.urlopen(req, timeout=120)
        zip_data = resp.read()
        print(f"  Downloaded {len(zip_data)/1024/1024:.1f} MB")
        
        # Extract and convert using ogr2ogr or fiona if available
        try:
            import fiona
            from shapely.geometry import shape, mapping
            
            with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                # Extract to temp dir
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    zf.extractall(tmpdir)
                    shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
                    if shp_files:
                        shp_path = os.path.join(tmpdir, shp_files[0])
                        with fiona.open(shp_path) as src:
                            for feat in src:
                                props = dict(feat['properties'])
                                if props.get('SLDL') == '041' or props.get('BASENAME') == '41':
                                    geom = mapping(shape(feat['geometry']))
                                    return {'type': 'Feature', 'properties': props, 'geometry': geom}
        except ImportError:
            print("  fiona not available, trying manual GeoJSON conversion...")
            # Try using subprocess with ogr2ogr
            import tempfile, subprocess
            with tempfile.TemporaryDirectory() as tmpdir:
                with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
                    zf.extractall(tmpdir)
                shp_files = [f for f in os.listdir(tmpdir) if f.endswith('.shp')]
                if shp_files:
                    shp_path = os.path.join(tmpdir, shp_files[0])
                    geojson_path = os.path.join(tmpdir, 'output.geojson')
                    result = subprocess.run(
                        ['ogr2ogr', '-f', 'GeoJSON', '-where', "SLDL='041'", geojson_path, shp_path],
                        capture_output=True, text=True
                    )
                    if result.returncode == 0 and os.path.exists(geojson_path):
                        with open(geojson_path) as f:
                            data = json.load(f)
                        if data.get('features'):
                            print(f"  ✓ Extracted HD-41 via ogr2ogr")
                            return data['features'][0]
                    else:
                        print(f"  ogr2ogr failed: {result.stderr}")
    except Exception as e:
        print(f"  Shapefile download failed: {e}")
    
    return None


def add_to_districts_json(feature):
    """Add HD-41 feature to the existing districts.json file."""
    # Load existing
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)
    
    # Check if HD-41 already exists
    existing = [f for f in districts['features'] if f.get('properties', {}).get('district_id') == 'HD-41']
    if existing:
        print("  HD-41 already in districts.json, replacing...")
        districts['features'] = [f for f in districts['features'] if f.get('properties', {}).get('district_id') != 'HD-41']
    
    # Add HD-41 with standardized properties
    props = feature.get('properties', {})
    new_feature = {
        'type': 'Feature',
        'properties': {
            'district_type': 'state_house',
            'district_id': 'HD-41',
            'district_name': 'TX State House District 41',
            'NAME': 'State House District 41',
            'BASENAME': '41',
            'SLDL': '041',
            'STATE': '48',
            'color': '#FF6347',
            **{k: v for k, v in props.items() if k not in ('district_type', 'district_id', 'district_name')}
        },
        'geometry': feature['geometry']
    }
    
    districts['features'].append(new_feature)
    
    with open(DISTRICTS_PATH, 'w') as f:
        json.dump(districts, f)
    
    print(f"  Added HD-41 to districts.json ({len(districts['features'])} total features)")


def point_in_polygon(x, y, polygon):
    """Ray casting algorithm."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def point_in_geometry(lng, lat, geometry):
    """Check if point is in a GeoJSON geometry."""
    gtype = geometry['type']
    if gtype == 'Polygon':
        return point_in_polygon(lng, lat, geometry['coordinates'][0])
    elif gtype == 'MultiPolygon':
        for poly in geometry['coordinates']:
            if point_in_polygon(lng, lat, poly[0]):
                return True
    return False


def assign_voters_to_hd41(geometry):
    """Assign state_house_district='HD-41' to voters whose precinct centroid is in HD-41."""
    print("\nAssigning voters to HD-41 using precinct centroids...")
    
    conn = sqlite3.connect(DB_PATH)
    
    # Get precinct centroids for Hidalgo County (HD-41 is in Hidalgo)
    precincts = conn.execute("""
        SELECT precinct, AVG(lat) as avg_lat, AVG(lng) as avg_lng, COUNT(*) as voters
        FROM voters
        WHERE county = 'Hidalgo' AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """).fetchall()
    
    print(f"  Testing {len(precincts)} precincts against HD-41 boundary...")
    
    hd41_precincts = []
    total_voters = 0
    for precinct, lat, lng, count in precincts:
        if point_in_geometry(lng, lat, geometry):
            hd41_precincts.append(precinct)
            total_voters += count
    
    print(f"  Found {len(hd41_precincts)} precincts in HD-41 ({total_voters} voters)")
    
    if not hd41_precincts:
        # Try all counties, not just Hidalgo
        print("  No Hidalgo precincts matched. Trying all counties...")
        precincts = conn.execute("""
            SELECT precinct, county, AVG(lat) as avg_lat, AVG(lng) as avg_lng, COUNT(*) as voters
            FROM voters
            WHERE precinct IS NOT NULL AND lat IS NOT NULL
            GROUP BY precinct, county
        """).fetchall()
        
        hd41_precincts = []
        total_voters = 0
        counties = set()
        for precinct, county, lat, lng, count in precincts:
            if point_in_geometry(lng, lat, {'type': geometry['type'], 'coordinates': geometry['coordinates']}):
                hd41_precincts.append((precinct, county))
                total_voters += count
                counties.add(county)
        
        print(f"  Found {len(hd41_precincts)} precincts in HD-41 across counties: {counties}")
        
        if hd41_precincts:
            # Update with county filter
            for precinct, county in hd41_precincts:
                conn.execute("""
                    UPDATE voters SET state_house_district = 'HD-41'
                    WHERE precinct = ? AND county = ?
                """, (precinct, county))
    else:
        # Update Hidalgo precincts
        placeholders = ','.join('?' * len(hd41_precincts))
        conn.execute(f"""
            UPDATE voters SET state_house_district = 'HD-41'
            WHERE precinct IN ({placeholders}) AND county = 'Hidalgo'
        """, hd41_precincts)
    
    conn.commit()
    
    # Verify
    assigned = conn.execute("SELECT COUNT(*) FROM voters WHERE state_house_district = 'HD-41'").fetchone()[0]
    print(f"\n✓ Assigned {assigned} voters to HD-41")
    
    conn.close()
    return assigned


def main():
    # Step 1: Download HD-41 boundary
    feature = download_and_extract_hd41()
    if not feature:
        print("ERROR: Could not download HD-41 boundary. Exiting.")
        sys.exit(1)
    
    # Step 2: Add to districts.json
    add_to_districts_json(feature)
    
    # Step 3: Assign voters
    assigned = assign_voters_to_hd41(feature['geometry'])
    
    if assigned == 0:
        print("\nWARNING: No voters assigned. The boundary may not overlap with geocoded voter data.")
        print("Check that Hidalgo County voters have lat/lng coordinates.")
    else:
        print(f"\n✓ Done! {assigned} voters now have state_house_district = 'HD-41'")
        print("Run: python3 deploy/refresh_hd41_all.py")


if __name__ == '__main__':
    main()
