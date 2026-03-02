#!/usr/bin/env python3
"""
Regenerate district cache files with COMPLETE data across ALL counties.
Uses district columns for Hidalgo County (fast) + polygon lookup for other counties (complete).
"""
import sqlite3
import json
import time
from pathlib import Path
from shapely.geometry import shape, Point

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_DIR = '/opt/whovoted/public/cache'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'
ELECTION_DATE = '2026-03-03'

def point_in_polygon(lng, lat, geometry):
    """Check if a point is inside a polygon using shapely."""
    try:
        point = Point(lng, lat)
        poly = shape(geometry)
        return poly.contains(point)
    except:
        return False

def get_district_column(district_id):
    """Determine which district column to use based on district_id format."""
    if district_id.startswith('TX-') and len(district_id) <= 5:
        return 'congressional_district'
    elif district_id.startswith('HD-'):
        return 'state_house_district'
    elif district_id.startswith('CC-'):
        return 'commissioner_district'
    return None

def get_vuids_for_district(conn, district_id, geometry):
    """
    Get ALL VUIDs for a district using:
    1. District columns for Hidalgo County voters (instant)
    2. Polygon lookup for voters in other counties (complete coverage)
    """
    vuids_set = set()
    
    # STEP 1: Get Hidalgo County voters using district column (fast!)
    district_col = get_district_column(district_id)
    if district_col:
        hidalgo_rows = conn.execute(f"""
            SELECT DISTINCT ve.vuid FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = ?
              AND v.{district_col} = ?
              AND v.county = 'Hidalgo'
              AND ve.party_voted IN ('Democratic', 'Republican')
        """, [ELECTION_DATE, district_id]).fetchall()
        
        hidalgo_vuids = {r[0] for r in hidalgo_rows}
        vuids_set.update(hidalgo_vuids)
        print(f"  Hidalgo (district column): {len(hidalgo_vuids):,} voters")
    
    # STEP 2: Get voters from OTHER counties using polygon lookup
    coords = geometry.get('coordinates', [])
    gtype = geometry.get('type', '')
    
    # Compute bounding box
    all_points = []
    if gtype == 'Polygon':
        all_points = coords[0]
    elif gtype == 'MultiPolygon':
        for poly in coords:
            all_points.extend(poly[0])
    
    if all_points:
        min_lng = min(p[0] for p in all_points)
        max_lng = max(p[0] for p in all_points)
        min_lat = min(p[1] for p in all_points)
        max_lat = max(p[1] for p in all_points)
        
        # Get candidates from bounding box (exclude Hidalgo since we already have them)
        bbox_rows = conn.execute("""
            SELECT DISTINCT ve.vuid, v.lng, v.lat FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = ?
              AND v.county != 'Hidalgo'
              AND v.lat BETWEEN ? AND ?
              AND v.lng BETWEEN ? AND ?
              AND ve.party_voted IN ('Democratic', 'Republican')
              AND v.lat IS NOT NULL AND v.lng IS NOT NULL
        """, [ELECTION_DATE, min_lat, max_lat, min_lng, max_lng]).fetchall()
        
        # Refine with point-in-polygon
        other_vuids = set()
        for r in bbox_rows:
            if point_in_polygon(r[1], r[2], geometry):
                other_vuids.add(r[0])
        
        vuids_set.update(other_vuids)
        print(f"  Other counties (polygon): {len(other_vuids):,} voters (from {len(bbox_rows):,} candidates)")
    
    return list(vuids_set)

def main():
    print("Loading districts...")
    with open(DISTRICTS_FILE, 'r') as f:
        districts_data = json.load(f)
    
    features = districts_data.get('features', [])
    print(f"Found {len(features)} districts\n")
    
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cached = 0
    
    for feature in features:
        props = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        district_name = props.get('district_name', 'Unknown')
        district_id = props.get('district_id', 'Unknown')
        
        print(f"\nCaching {district_name} ({district_id})...")
        t0 = time.time()
        
        try:
            # Get ALL VUIDs across all counties
            vuids = get_vuids_for_district(conn, district_id, geometry)
            
            if not vuids:
                print("  ✗ No voters found")
                continue
            
            print(f"  Total: {len(vuids):,} voters")
            
            # Create temp table for efficient queries
            conn.execute("CREATE TEMP TABLE IF NOT EXISTS _cache_vuids(vuid TEXT PRIMARY KEY)")
            conn.execute("DELETE FROM _cache_vuids")
            conn.executemany("INSERT OR IGNORE INTO _cache_vuids(vuid) VALUES(?)", [(v,) for v in vuids])
            
            # Core stats
            core = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
                    SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep,
                    SUM(CASE WHEN v.sex = 'F' THEN 1 ELSE 0 END) as female,
                    SUM(CASE WHEN v.sex = 'M' THEN 1 ELSE 0 END) as male,
                    SUM(CASE WHEN ve.party_voted = 'Democratic' AND v.sex = 'F' THEN 1 ELSE 0 END) as dem_female,
                    SUM(CASE WHEN ve.party_voted = 'Democratic' AND v.sex = 'M' THEN 1 ELSE 0 END) as dem_male,
                    SUM(CASE WHEN ve.party_voted = 'Republican' AND v.sex = 'F' THEN 1 ELSE 0 END) as rep_female,
                    SUM(CASE WHEN ve.party_voted = 'Republican' AND v.sex = 'M' THEN 1 ELSE 0 END) as rep_male
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                INNER JOIN _cache_vuids t ON ve.vuid = t.vuid
                WHERE ve.election_date = ?
            """, [ELECTION_DATE]).fetchone()
            
            total = core['total'] or 0
            dem = core['dem'] or 0
            rep = core['rep'] or 0
            
            # Flips
            flip_rows = conn.execute("""
                SELECT ve_cur.party_voted as to_p, ve_prev.party_voted as from_p, COUNT(*) as cnt
                FROM voter_elections ve_cur
                INNER JOIN _cache_vuids t ON ve_cur.vuid = t.vuid
                INNER JOIN voter_elections ve_prev ON ve_cur.vuid = ve_prev.vuid
                WHERE ve_cur.election_date = ?
                  AND ve_prev.election_date = (
                      SELECT MAX(ve2.election_date) FROM voter_elections ve2
                      WHERE ve2.vuid = ve_cur.vuid AND ve2.election_date < ?
                        AND ve2.party_voted IN ('Democratic', 'Republican'))
                  AND ve_cur.party_voted != ve_prev.party_voted
                  AND ve_cur.party_voted IN ('Democratic', 'Republican')
                  AND ve_prev.party_voted IN ('Democratic', 'Republican')
                GROUP BY ve_cur.party_voted, ve_prev.party_voted
            """, [ELECTION_DATE, ELECTION_DATE]).fetchall()
            r2d = sum(r['cnt'] for r in flip_rows if r['from_p'] == 'Republican' and r['to_p'] == 'Democratic')
            d2r = sum(r['cnt'] for r in flip_rows if r['from_p'] == 'Democratic' and r['to_p'] == 'Republican')
            
            # New voters - ONLY voters with NO prior primary history
            new_row = conn.execute("""
                SELECT
                    COUNT(*) as new_total,
                    SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as new_dem,
                    SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as new_rep
                FROM voter_elections ve
                INNER JOIN _cache_vuids t ON ve.vuid = t.vuid
                WHERE ve.election_date = ?
                  AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
                      WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                        AND ve2.party_voted IN ('Democratic', 'Republican'))
            """, [ELECTION_DATE, ELECTION_DATE]).fetchone()
            new_total = new_row['new_total'] or 0
            new_dem = new_row['new_dem'] or 0
            new_rep = new_row['new_rep'] or 0
            
            # New voter age/gender breakdown
            new_age_gender = {}
            nag_rows = conn.execute("""
                SELECT
                    CASE
                        WHEN v.birth_year BETWEEN 2002 AND 2008 THEN '18-24'
                        WHEN v.birth_year BETWEEN 1992 AND 2001 THEN '25-34'
                        WHEN v.birth_year BETWEEN 1982 AND 1991 THEN '35-44'
                        WHEN v.birth_year BETWEEN 1972 AND 1981 THEN '45-54'
                        WHEN v.birth_year BETWEEN 1962 AND 1971 THEN '55-64'
                        WHEN v.birth_year BETWEEN 1952 AND 1961 THEN '65-74'
                        WHEN v.birth_year > 0 AND v.birth_year < 1952 THEN '75+'
                        ELSE 'Unknown'
                    END as age_group,
                    v.sex, COUNT(*) as cnt
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                INNER JOIN _cache_vuids t ON ve.vuid = t.vuid
                WHERE ve.election_date = ?
                  AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
                      WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                        AND ve2.party_voted IN ('Democratic', 'Republican'))
                GROUP BY age_group, v.sex
            """, [ELECTION_DATE, ELECTION_DATE]).fetchall()
            for row in nag_rows:
                ag, sex, cnt = row['age_group'], row['sex'] or 'U', row['cnt']
                if ag not in new_age_gender:
                    new_age_gender[ag] = {'total': 0, 'female': 0, 'male': 0}
                new_age_gender[ag]['total'] += cnt
                if sex == 'F': new_age_gender[ag]['female'] += cnt
                elif sex == 'M': new_age_gender[ag]['male'] += cnt
            
            # Age group breakdown
            age_groups = {}
            ag_rows = conn.execute("""
                SELECT
                    CASE
                        WHEN v.birth_year BETWEEN 2002 AND 2008 THEN '18-24'
                        WHEN v.birth_year BETWEEN 1992 AND 2001 THEN '25-34'
                        WHEN v.birth_year BETWEEN 1982 AND 1991 THEN '35-44'
                        WHEN v.birth_year BETWEEN 1972 AND 1981 THEN '45-54'
                        WHEN v.birth_year BETWEEN 1962 AND 1971 THEN '55-64'
                        WHEN v.birth_year BETWEEN 1952 AND 1961 THEN '65-74'
                        WHEN v.birth_year > 0 AND v.birth_year < 1952 THEN '75+'
                        ELSE 'Unknown'
                    END as age_group,
                    ve.party_voted, COUNT(*) as cnt
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                INNER JOIN _cache_vuids t ON ve.vuid = t.vuid
                WHERE ve.election_date = ?
                GROUP BY age_group, ve.party_voted
            """, [ELECTION_DATE]).fetchall()
            for row in ag_rows:
                ag, party, cnt = row['age_group'], row['party_voted'], row['cnt']
                if ag not in age_groups:
                    age_groups[ag] = {'total': 0, 'dem': 0, 'rep': 0}
                age_groups[ag]['total'] += cnt
                if party == 'Democratic': age_groups[ag]['dem'] += cnt
                elif party == 'Republican': age_groups[ag]['rep'] += cnt
            
            # 2024 comparison
            comp = conn.execute("""
                SELECT
                    COUNT(*) as total_2024,
                    SUM(CASE WHEN party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem_2024,
                    SUM(CASE WHEN party_voted = 'Republican' THEN 1 ELSE 0 END) as rep_2024
                FROM voter_elections ve
                INNER JOIN _cache_vuids t ON ve.vuid = t.vuid
                WHERE ve.election_date = '2024-03-05'
            """).fetchone()
            total_2024 = comp['total_2024'] or 0
            dem_2024 = comp['dem_2024'] or 0
            rep_2024 = comp['rep_2024'] or 0
            
            # County breakdown
            county_breakdown = {}
            cb_rows = conn.execute("""
                SELECT v.county, ve.party_voted, COUNT(*) as cnt
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                INNER JOIN _cache_vuids t ON ve.vuid = t.vuid
                WHERE ve.election_date = ?
                  AND ve.party_voted IN ('Democratic', 'Republican')
                GROUP BY v.county, ve.party_voted
            """, [ELECTION_DATE]).fetchall()
            for row in cb_rows:
                county = row['county'] or 'Unknown'
                party, cnt = row['party_voted'], row['cnt']
                if county not in county_breakdown:
                    county_breakdown[county] = {'total': 0, 'dem': 0, 'rep': 0}
                county_breakdown[county]['total'] += cnt
                if party == 'Democratic': county_breakdown[county]['dem'] += cnt
                elif party == 'Republican': county_breakdown[county]['rep'] += cnt
            
            dem_share = round(dem / (dem + rep) * 100, 1) if (dem + rep) else 0
            dem_share_2024 = round(dem_2024 / (dem_2024 + rep_2024) * 100, 1) if (dem_2024 + rep_2024) else 0
            
            # Build complete cache object
            report = {
                'district_id': district_id,
                'district_name': district_name,
                'election_date': ELECTION_DATE,
                'total': total,
                'dem': dem,
                'rep': rep,
                'dem_share': dem_share,
                'new_total': new_total,
                'new_dem': new_dem,
                'new_rep': new_rep,
                'r2d': r2d,
                'd2r': d2r,
                'total_2024': total_2024,
                'dem_2024': dem_2024,
                'rep_2024': rep_2024,
                'dem_share_2024': dem_share_2024,
                'female': core['female'] or 0,
                'male': core['male'] or 0,
                'dem_female': core['dem_female'] or 0,
                'dem_male': core['dem_male'] or 0,
                'rep_female': core['rep_female'] or 0,
                'rep_male': core['rep_male'] or 0,
                'age_groups': age_groups,
                'new_age_gender': new_age_gender,
                'county_breakdown': county_breakdown,
                'generated_at': time.time(),
            }
            
            # Save to cache file
            safe_name = district_name.replace(' ', '_').replace('/', '_')
            cache_file = Path(CACHE_DIR) / f'district_report_{safe_name}.json'
            with open(cache_file, 'w') as f:
                json.dump(report, f, separators=(',', ':'))
            
            cached += 1
            elapsed = time.time() - t0
            print(f"  ✓ Cached in {elapsed:.1f}s")
            print(f"    {total:,} total | {dem:,} D ({dem_share}%) | {rep:,} R | {new_total:,} new voters")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            import traceback
            traceback.print_exc()
    
    conn.execute("DROP TABLE IF EXISTS _cache_vuids")
    conn.close()
    
    print(f"\n✅ Successfully cached {cached} districts")

if __name__ == '__main__':
    main()
