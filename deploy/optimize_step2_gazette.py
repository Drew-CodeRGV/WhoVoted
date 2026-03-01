#!/usr/bin/env python3
"""
Step 2: Pre-compute gazette insights.
Run this AFTER Step 1 (indexes) and AFTER each scraper run.
Run time: ~2-5 minutes (depends on data size)
"""
import sqlite3
import json
import time
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_DIR = '/opt/whovoted/public/cache'
CACHE_FILE = Path(CACHE_DIR) / 'gazette_insights.json'

def main():
    print("\n" + "="*70)
    print("STEP 2: Pre-computing Gazette Insights")
    print("="*70 + "\n")
    
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    insights = {}
    overall_start = time.time()
    
    # Simple counts (fast with indexes)
    print("Computing turnout stats...", end=' ', flush=True)
    t0 = time.time()
    insights['ev_2022'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND voting_method='early-voting'").fetchone()[0]
    insights['ed_2022'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND voting_method='election-day'").fetchone()[0]
    insights['ev_2024'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND voting_method='early-voting'").fetchone()[0]
    insights['ed_2024'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND voting_method='election-day'").fetchone()[0]
    insights['ev_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03'").fetchone()[0]
    insights['total_2022'] = insights['ev_2022'] + insights['ed_2022']
    insights['total_2024'] = insights['ev_2024'] + insights['ed_2024']
    print(f"✓ {time.time()-t0:.1f}s")
    
    # Party breakdown (fast with indexes)
    print("Computing party breakdown...", end=' ', flush=True)
    t0 = time.time()
    insights['dem_2022'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND party_voted='Democratic'").fetchone()[0]
    insights['rep_2022'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND party_voted='Republican'").fetchone()[0]
    insights['dem_2024'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND party_voted='Democratic'").fetchone()[0]
    insights['rep_2024'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND party_voted='Republican'").fetchone()[0]
    insights['dem_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Democratic'").fetchone()[0]
    insights['rep_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Republican'").fetchone()[0]
    
    insights['dem_share_2022'] = round(insights['dem_2022'] / (insights['dem_2022'] + insights['rep_2022']) * 100, 1) if (insights['dem_2022'] + insights['rep_2022']) else 0
    insights['dem_share_2024'] = round(insights['dem_2024'] / (insights['dem_2024'] + insights['rep_2024']) * 100, 1) if (insights['dem_2024'] + insights['rep_2024']) else 0
    insights['dem_share_2026'] = round(insights['dem_2026'] / (insights['dem_2026'] + insights['rep_2026']) * 100, 1) if (insights['dem_2026'] + insights['rep_2026']) else 0
    insights['pct_of_2024'] = round(insights['ev_2026'] / insights['total_2024'] * 100) if insights['total_2024'] else 0
    print(f"✓ {time.time()-t0:.1f}s")
    
    # Flips (optimized with indexes - should be faster now)
    print("Computing party flips...", end=' ', flush=True)
    t0 = time.time()
    for year, edate in [('2024', '2024-03-05'), ('2026', '2026-03-03')]:
        rows = conn.execute("""
            SELECT ve_current.party_voted as to_p, ve_prev.party_voted as from_p, COUNT(*) as cnt
            FROM voter_elections ve_current
            JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
            WHERE ve_current.election_date = ?
                AND ve_prev.election_date = (
                    SELECT MAX(ve2.election_date) FROM voter_elections ve2
                    WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
                        AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
                AND ve_current.party_voted != ve_prev.party_voted
                AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
            GROUP BY ve_current.party_voted, ve_prev.party_voted
        """, (edate,)).fetchall()
        r2d = sum(r[2] for r in rows if r[1] == 'Republican' and r[0] == 'Democratic')
        d2r = sum(r[2] for r in rows if r[1] == 'Democratic' and r[0] == 'Republican')
        insights[f'r2d_{year}'] = r2d
        insights[f'd2r_{year}'] = d2r
    print(f"✓ {time.time()-t0:.1f}s")
    
    # New voters (now fast with denormalized column!)
    print("Computing new voters...", end=' ', flush=True)
    t0 = time.time()
    
    # Use the pre-computed is_new_voter flag
    new_2026 = conn.execute("""
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND is_new_voter = 1
    """).fetchone()[0]
    insights['new_2026'] = new_2026
    
    new_dem_2026 = conn.execute("""
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND party_voted = 'Democratic' AND is_new_voter = 1
    """).fetchone()[0]
    insights['new_dem_2026'] = new_dem_2026
    
    new_rep_2026 = conn.execute("""
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND party_voted = 'Republican' AND is_new_voter = 1
    """).fetchone()[0]
    insights['new_rep_2026'] = new_rep_2026
    print(f"✓ {time.time()-t0:.1f}s")
    
    # Gender, age, turnout stats (simplified for speed)
    print("Computing demographics...", end=' ', flush=True)
    t0 = time.time()
    
    # Gender
    insights['female_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid WHERE ve.election_date='2026-03-03' AND v.sex='F'").fetchone()[0]
    insights['male_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid WHERE ve.election_date='2026-03-03' AND v.sex='M'").fetchone()[0]
    insights['dem_female_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid WHERE ve.election_date='2026-03-03' AND ve.party_voted='Democratic' AND v.sex='F'").fetchone()[0]
    insights['dem_male_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid WHERE ve.election_date='2026-03-03' AND ve.party_voted='Democratic' AND v.sex='M'").fetchone()[0]
    insights['rep_female_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid WHERE ve.election_date='2026-03-03' AND ve.party_voted='Republican' AND v.sex='F'").fetchone()[0]
    insights['rep_male_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections ve JOIN voters v ON ve.vuid = v.vuid WHERE ve.election_date='2026-03-03' AND ve.party_voted='Republican' AND v.sex='M'").fetchone()[0]
    
    # Age groups
    age_rows = conn.execute("""
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
        WHERE ve.election_date = '2026-03-03'
        GROUP BY age_group, ve.party_voted
    """).fetchall()
    
    age_groups_2026 = {}
    for row in age_rows:
        ag, party, cnt = row[0], row[1], row[2]
        if ag not in age_groups_2026:
            age_groups_2026[ag] = {'total': 0, 'dem': 0, 'rep': 0}
        age_groups_2026[ag]['total'] += cnt
        if party == 'Democratic':
            age_groups_2026[ag]['dem'] += cnt
        elif party == 'Republican':
            age_groups_2026[ag]['rep'] += cnt
    insights['age_groups_2026'] = age_groups_2026
    
    # Turnout comparison
    both_24_26 = conn.execute("""
        SELECT COUNT(DISTINCT ve1.vuid)
        FROM voter_elections ve1
        JOIN voter_elections ve2 ON ve1.vuid = ve2.vuid
        WHERE ve1.election_date = '2024-03-05' AND ve2.election_date = '2026-03-03'
    """).fetchone()[0]
    insights['both_24_26'] = both_24_26
    
    voted_24_not_26 = conn.execute("""
        SELECT COUNT(DISTINCT ve1.vuid)
        FROM voter_elections ve1
        WHERE ve1.election_date = '2024-03-05'
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve1.vuid AND ve2.election_date = '2026-03-03')
    """).fetchone()[0]
    insights['voted_24_not_26'] = voted_24_not_26
    
    # Last updated
    last_updated = conn.execute("SELECT MAX(last_updated) FROM election_summary WHERE election_date='2026-03-03'").fetchone()[0]
    insights['last_updated'] = last_updated
    
    # Add generation timestamp
    from datetime import datetime
    insights['generated_at'] = datetime.now().isoformat()
    insights['generated_timestamp'] = datetime.now().strftime('%Y-%m-%d %I:%M %p')
    
    # Stub for new_age_gender_2026 (skip for now - too slow)
    insights['new_age_gender_2026'] = {}
    
    print(f"✓ {time.time()-t0:.1f}s")
    
    conn.close()
    
    # Save to cache
    print(f"\nSaving to {CACHE_FILE}...", end=' ', flush=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(insights, f, separators=(',', ':'))
    print("✓")
    
    total_time = time.time() - overall_start
    print(f"\n{'='*70}")
    print(f"✅ Gazette insights cached in {total_time:.1f}s")
    print(f"{'='*70}\n")
    
    print("Gazette will now load instantly!")
    print("Re-run this script after each scraper run to update data.\n")
    
    # Pre-compute county reports
    print("\n" + "="*70)
    print("Pre-computing County Reports")
    print("="*70 + "\n")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get all unique county/election_date/voting_method combinations
    print("Finding datasets to cache...", end=' ', flush=True)
    datasets = conn.execute("""
        SELECT DISTINCT v.county, ve.election_date, ve.voting_method
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county IS NOT NULL AND ve.election_date IS NOT NULL
        ORDER BY ve.election_date DESC, v.county
    """).fetchall()
    print(f"✓ Found {len(datasets)} datasets")
    
    cached_count = 0
    for ds in datasets:
        county, election_date, voting_method = ds[0], ds[1], ds[2]
        method_str = voting_method or 'all'
        
        print(f"  Caching {county}/{election_date}/{method_str}...", end=' ', flush=True)
        t0 = time.time()
        
        try:
            # Build WHERE clause
            where_base = "WHERE v.county = ? AND ve.election_date = ?"
            params_base = [county, election_date]
            if voting_method:
                where_base += " AND ve.voting_method = ?"
                params_base.append(voting_method)
            
            report = {
                'county': county,
                'election_date': election_date,
                'voting_method': voting_method or 'all',
            }
            
            # Total voters
            report['total_voters'] = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                {where_base}
            """, params_base).fetchone()[0]
            
            # Party breakdown
            report['dem_count'] = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                {where_base} AND ve.party_voted = 'Democratic'
            """, params_base).fetchone()[0]
            
            report['rep_count'] = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                {where_base} AND ve.party_voted = 'Republican'
            """, params_base).fetchone()[0]
            
            # New voters
            report['new_voters'] = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                {where_base} AND ve.is_new_voter = 1
            """, params_base).fetchone()[0]
            
            report['new_dem'] = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                {where_base} AND ve.party_voted = 'Democratic' AND ve.is_new_voter = 1
            """, params_base).fetchone()[0]
            
            report['new_rep'] = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                {where_base} AND ve.party_voted = 'Republican' AND ve.is_new_voter = 1
            """, params_base).fetchone()[0]
            
            # Flips
            flip_rows = conn.execute(f"""
                SELECT ve_current.party_voted as to_p, ve_prev.party_voted as from_p, COUNT(*) as cnt
                FROM voter_elections ve_current
                JOIN voters v ON ve_current.vuid = v.vuid
                JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
                WHERE v.county = ? AND ve_current.election_date = ?
                    AND ve_prev.election_date = (
                        SELECT MAX(ve2.election_date) FROM voter_elections ve2
                        WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
                            AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
                    AND ve_current.party_voted != ve_prev.party_voted
                    AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
                GROUP BY ve_current.party_voted, ve_prev.party_voted
            """, [county, election_date]).fetchall()
            
            report['r2d'] = sum(r[2] for r in flip_rows if r[1] == 'Republican' and r[0] == 'Democratic')
            report['d2r'] = sum(r[2] for r in flip_rows if r[1] == 'Democratic' and r[0] == 'Republican')
            
            # Gender
            report['female_count'] = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                {where_base} AND v.sex = 'F'
            """, params_base).fetchone()[0]
            
            report['male_count'] = conn.execute(f"""
                SELECT COUNT(*) FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                {where_base} AND v.sex = 'M'
            """, params_base).fetchone()[0]
            
            # Age groups
            age_rows = conn.execute(f"""
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
                {where_base}
                GROUP BY age_group, ve.party_voted
            """, params_base).fetchall()
            
            age_groups = {}
            for row in age_rows:
                ag, party, cnt = row[0], row[1], row[2]
                if ag not in age_groups:
                    age_groups[ag] = {'total': 0, 'dem': 0, 'rep': 0}
                age_groups[ag]['total'] += cnt
                if party == 'Democratic':
                    age_groups[ag]['dem'] += cnt
                elif party == 'Republican':
                    age_groups[ag]['rep'] += cnt
            report['age_groups'] = age_groups
            
            # Calculate percentages
            report['dem_share'] = round(report['dem_count'] / (report['dem_count'] + report['rep_count']) * 100, 1) if (report['dem_count'] + report['rep_count']) else 0
            report['new_dem_pct'] = round(report['new_dem'] / report['new_voters'] * 100, 1) if report['new_voters'] else 0
            report['female_pct'] = round(report['female_count'] / (report['female_count'] + report['male_count']) * 100, 1) if (report['female_count'] + report['male_count']) else 0
            
            # Last updated
            last_row = conn.execute(f"""
                SELECT MAX(ve.created_at) FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                {where_base}
            """, params_base).fetchone()
            report['last_updated'] = last_row[0] if last_row and last_row[0] else None
            
            from datetime import datetime
            report['generated_at'] = datetime.now().isoformat()
            
            # Save to cache file
            cache_file = Path(CACHE_DIR) / f'county_report_{county}_{election_date}_{method_str}.json'
            with open(cache_file, 'w') as f:
                json.dump(report, f, separators=(',', ':'))
            
            cached_count += 1
            print(f"✓ {time.time()-t0:.1f}s")
            
        except Exception as e:
            print(f"✗ Error: {e}")
    
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ Cached {cached_count} county reports")
    print(f"{'='*70}\n")
    
    # Pre-compute district reports
    print("\n" + "="*70)
    print("Pre-computing District Reports")
    print("="*70 + "\n")
    
    # Load districts from JSON file
    import json
    districts_file = Path('/opt/whovoted/public/data/districts.json')
    if not districts_file.exists():
        print("⚠ districts.json not found, skipping district reports")
        return
    
    with open(districts_file, 'r') as f:
        districts_data = json.load(f)
    
    districts = districts_data.get('features', [])
    print(f"Found {len(districts)} districts to cache")
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cached_districts = 0
    for feature in districts:
        props = feature.get('properties', {})
        geometry = feature.get('geometry', {})
        district_name = props.get('district_name', 'Unknown')
        district_type = props.get('district_type', 'unknown')
        
        print(f"  Caching {district_name}...", end=' ', flush=True)
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
            
            # Get voters in bounding box (for most recent election)
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
            
            # Point-in-polygon check (simplified ray-casting)
            def point_in_polygon(lng, lat, polygon):
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
                gtype = geom.get('type', '')
                coords = geom.get('coordinates', [])
                if gtype == 'Polygon':
                    return point_in_polygon(lng, lat, coords[0])
                elif gtype == 'MultiPolygon':
                    return any(point_in_polygon(lng, lat, poly[0]) for poly in coords)
                return False
            
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
                print("✗ No voters in district")
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
                'district_name': district_name,
                'district_type': district_type,
                'total': total,
                'dem': dem,
                'rep': rep,
                'new_voters': new_voters,
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
            
            cached_districts += 1
            print(f"✓ {time.time()-t0:.1f}s ({total} voters)")
            
        except Exception as e:
            print(f"✗ Error: {e}")
    
    conn.close()
    
    print(f"\n{'='*70}")
    print(f"✅ Cached {cached_districts} district reports")
    print(f"{'='*70}\n")

if __name__ == '__main__':
    main()
