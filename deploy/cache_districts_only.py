#!/usr/bin/env python3
"""Quick script to cache district reports only (not historical county data)."""
import sqlite3
import json
import time
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_DIR = '/opt/whovoted/public/cache'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'

def point_in_polygon(lng, lat, polygon):
    """Ray-casting algorithm for point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def point_in_feature(lng, lat, geom):
    """Check if point is inside a GeoJSON geometry."""
    gtype = geom.get('type', '')
    coords = geom.get('coordinates', [])
    if gtype == 'Polygon':
        return point_in_polygon(lng, lat, coords[0])
    elif gtype == 'MultiPolygon':
        return any(point_in_polygon(lng, lat, poly[0]) for poly in coords)
    return False

def main():
    print("Loading districts...")
    with open(DISTRICTS_FILE, 'r') as f:
        districts_data = json.load(f)
    
    districts = districts_data.get('features', [])
    print(f"Found {len(districts)} districts")
    
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cached = 0
    for feature in districts:
        props = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        district_name = props.get('district_name', 'Unknown')
        district_id = props.get('district_id', 'Unknown')
        
        print(f"Caching {district_name}...", end=' ', flush=True)
        t0 = time.time()
        
        try:
            # Get polygon coordinates
            coords = geometry.get('coordinates', [])
            gtype = geometry.get('type', '')
            
            # Compute bounding box
            all_points = []
            if gtype == 'Polygon':
                all_points = coords[0] if coords else []
            elif gtype == 'MultiPolygon':
                for poly in coords:
                    if poly and poly[0]:
                        all_points.extend(poly[0])
            
            if not all_points:
                print("✗ No coordinates")
                continue
            
            min_lng = min(p[0] for p in all_points)
            max_lng = max(p[0] for p in all_points)
            min_lat = min(p[1] for p in all_points)
            max_lat = max(p[1] for p in all_points)
            
            # Get voters in bounding box (2026 only)
            bbox_voters = conn.execute("""
                SELECT DISTINCT ve.vuid, v.lng, v.lat, v.county, ve.party_voted
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE ve.election_date = '2026-03-03'
                  AND v.lat BETWEEN ? AND ?
                  AND v.lng BETWEEN ? AND ?
                  AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
                  AND v.lat IS NOT NULL AND v.lng IS NOT NULL
            """, [min_lat, max_lat, min_lng, max_lng]).fetchall()
            
            # Filter voters inside polygon
            vuids_in_district = []
            county_breakdown = {}
            for row in bbox_voters:
                if point_in_feature(row['lng'], row['lat'], geometry):
                    vuids_in_district.append(row['vuid'])
                    county = row['county'] or 'Unknown'
                    party = row['party_voted']
                    if county not in county_breakdown:
                        county_breakdown[county] = {'total': 0, 'dem': 0, 'rep': 0}
                    county_breakdown[county]['total'] += 1
                    if party == 'Democratic':
                        county_breakdown[county]['dem'] += 1
                    elif party == 'Republican':
                        county_breakdown[county]['rep'] += 1
            
            if not vuids_in_district:
                print("✗ No voters")
                continue
            
            # Compute stats
            total = len(vuids_in_district)
            dem = sum(1 for v in bbox_voters if v['vuid'] in vuids_in_district and v['party_voted'] == 'Democratic')
            rep = sum(1 for v in bbox_voters if v['vuid'] in vuids_in_district and v['party_voted'] == 'Republican')
            
            # New voters
            new_voters = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections
                WHERE vuid IN ({','.join('?' * len(vuids_in_district))})
                  AND election_date = '2026-03-03'
                  AND is_new_voter = 1
            """, vuids_in_district).fetchone()[0]
            
            new_dem = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections
                WHERE vuid IN ({','.join('?' * len(vuids_in_district))})
                  AND election_date = '2026-03-03'
                  AND party_voted = 'Democratic'
                  AND is_new_voter = 1
            """, vuids_in_district).fetchone()[0]
            
            new_rep = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections
                WHERE vuid IN ({','.join('?' * len(vuids_in_district))})
                  AND election_date = '2026-03-03'
                  AND party_voted = 'Republican'
                  AND is_new_voter = 1
            """, vuids_in_district).fetchone()[0]
            
            # Flips
            flip_rows = conn.execute(f"""
                SELECT ve_current.party_voted as to_p, ve_prev.party_voted as from_p, COUNT(*) as cnt
                FROM voter_elections ve_current
                JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
                WHERE ve_current.vuid IN ({','.join('?' * len(vuids_in_district))})
                  AND ve_current.election_date = '2026-03-03'
                  AND ve_prev.election_date = (
                      SELECT MAX(ve2.election_date) FROM voter_elections ve2
                      WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < '2026-03-03'
                          AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
                  AND ve_current.party_voted != ve_prev.party_voted
                  AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
                GROUP BY ve_current.party_voted, ve_prev.party_voted
            """, vuids_in_district).fetchall()
            
            r2d = sum(r[2] for r in flip_rows if r[1] == 'Republican' and r[0] == 'Democratic')
            d2r = sum(r[2] for r in flip_rows if r[1] == 'Democratic' and r[0] == 'Republican')
            
            report = {
                'district_id': district_id,
                'district_name': district_name,
                'total': total,
                'dem': dem,
                'rep': rep,
                'dem_share': round(dem / (dem + rep) * 100, 1) if (dem + rep) else 0,
                'new_total': new_voters,
                'new_dem': new_dem,
                'new_rep': new_rep,
                'r2d': r2d,
                'd2r': d2r,
                'county_breakdown': county_breakdown,
                'generated_at': time.time(),
            }
            
            # Save to cache file
            safe_name = district_name.replace(' ', '_').replace('/', '_')
            cache_file = Path(CACHE_DIR) / f'district_report_{safe_name}.json'
            with open(cache_file, 'w') as f:
                json.dump(report, f, separators=(',', ':'))
            
            cached += 1
            print(f"✓ {time.time()-t0:.1f}s ({total} voters)")
            
        except Exception as e:
            print(f"✗ Error: {e}")
    
    conn.close()
    
    print(f"\n✅ Cached {cached} district reports")

if __name__ == '__main__':
    main()
