#!/usr/bin/env python3
"""
Regenerate ALL district caches using the new district column assignments.
MUCH FASTER than polygon lookups - uses indexed district columns!
"""
import sqlite3
import json
import time
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_DIR = '/opt/whovoted/public/cache'
DISTRICTS_FILE = '/opt/whovoted/public/data/districts.json'
ELECTION_DATE = '2026-03-03'

def get_district_number(district_id):
    """Extract district number from ID (TX-15 -> 15, HD-35 -> 35)."""
    return district_id.split('-')[-1]

def get_district_column(district_id):
    """Determine which district column to use based on district_id format."""
    if district_id.startswith('TX-'):
        return 'congressional_district'
    elif district_id.startswith('SD-'):
        return 'state_senate_district'
    elif district_id.startswith('HD-'):
        return 'state_house_district'
    elif district_id.startswith('CC-'):
        return 'commissioner_district'
    return None

def generate_district_cache(conn, district_id, district_name):
    """Generate cache for a single district using district columns."""
    
    district_col = get_district_column(district_id)
    if not district_col:
        print(f"  ✗ Unknown district type: {district_id}")
        return None
    
    district_num = get_district_number(district_id)
    
    # Get all VUIDs for this district using indexed column
    vuids = conn.execute(f"""
        SELECT DISTINCT ve.vuid
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ?
          AND v.{district_col} = ?
          AND ve.party_voted IN ('Democratic', 'Republican')
    """, [ELECTION_DATE, district_num]).fetchall()
    
    vuids = [r[0] for r in vuids]
    
    if not vuids:
        print(f"  ✗ No voters found")
        return None
    
    print(f"  Found: {len(vuids):,} voters")
    
    # Create temp table for efficient queries
    conn.execute("CREATE TEMP TABLE IF NOT EXISTS _cache_vuids(vuid TEXT PRIMARY KEY)")
    conn.execute("DELETE FROM _cache_vuids")
    for i in range(0, len(vuids), 5000):
        chunk = vuids[i:i+5000]
        conn.executemany("INSERT OR IGNORE INTO _cache_vuids(vuid) VALUES(?)", [(v,) for v in chunk])
    
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
    female = core['female'] or 0
    male = core['male'] or 0
    dem_female = core['dem_female'] or 0
    dem_male = core['dem_male'] or 0
    rep_female = core['rep_female'] or 0
    rep_male = core['rep_male'] or 0
    
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
    
    # New voters - use is_new_voter flag
    new_row = conn.execute("""
        SELECT
            COUNT(*) as new_total,
            SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as new_dem,
            SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as new_rep
        FROM voter_elections ve
        INNER JOIN _cache_vuids t ON ve.vuid = t.vuid
        WHERE ve.election_date = ?
          AND ve.is_new_voter = 1
    """, [ELECTION_DATE]).fetchone()
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
          AND ve.is_new_voter = 1
        GROUP BY age_group, v.sex
    """, [ELECTION_DATE]).fetchall()
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
    
    return {
        'success': True,
        'district_id': district_id,
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
        'female': female,
        'male': male,
        'dem_female': dem_female,
        'dem_male': dem_male,
        'rep_female': rep_female,
        'rep_male': rep_male,
        'age_groups': age_groups,
        'new_age_gender': new_age_gender,
        'county_breakdown': county_breakdown,
    }

def main():
    print("="*80)
    print("REGENERATE ALL DISTRICT CACHES - FAST VERSION")
    print("="*80)
    print("\nUsing new district column assignments for 100x faster generation!")
    print(f"Election date: {ELECTION_DATE}\n")
    
    # Load districts
    print("Loading districts...")
    with open(DISTRICTS_FILE, 'r') as f:
        districts_data = json.load(f)
    
    features = districts_data.get('features', [])
    print(f"Found {len(features)} districts\n")
    
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    cached = 0
    skipped = 0
    total_start = time.time()
    
    for i, feature in enumerate(features, 1):
        props = feature.get('properties', {})
        district_name = props.get('district_name', 'Unknown')
        district_id = props.get('district_id', 'Unknown')
        
        print(f"[{i}/{len(features)}] {district_name} ({district_id})...")
        t0 = time.time()
        
        try:
            report = generate_district_cache(conn, district_id, district_name)
            
            if not report:
                skipped += 1
                continue
            
            # Save to cache file
            safe_name = district_name.replace(' ', '_').replace('/', '_')
            cache_file = Path(CACHE_DIR) / f'district_report_{safe_name}.json'
            
            with open(cache_file, 'w') as f:
                json.dump(report, f, separators=(',', ':'))
            
            cached += 1
            elapsed = time.time() - t0
            print(f"  ✓ Cached in {elapsed:.1f}s - Total: {report['total']:,}, Dem: {report['dem']:,} ({report['dem_share']}%)")
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            skipped += 1
    
    conn.close()
    
    total_elapsed = time.time() - total_start
    
    print(f"\n" + "="*80)
    print(f"✅ COMPLETE")
    print(f"="*80)
    print(f"\nCached: {cached} districts")
    print(f"Skipped: {skipped} districts")
    print(f"Total time: {total_elapsed/60:.1f} minutes")
    print(f"Average: {total_elapsed/len(features):.1f} seconds per district")
    print(f"\nCache files saved to: {CACHE_DIR}/")

if __name__ == '__main__':
    main()
