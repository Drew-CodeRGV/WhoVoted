#!/usr/bin/env python3
"""
Performance optimization: Add indexes and pre-compute insights.
Run after each scrape to ensure lightning-fast queries.
"""
import sqlite3
import json
import time
import sys
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_DIR = '/opt/whovoted/public/cache'
STATUS_FILE = '/opt/whovoted/data/optimization_status.json'

def write_status(status):
    """Write current status to JSON file for monitoring."""
    try:
        with open(STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not write status file: {e}")

def add_indexes(conn):
    """Add all missing indexes for fast lookups."""
    print("Adding database indexes...")
    write_status({
        'stage': 'indexes',
        'status': 'running',
        'message': 'Adding database indexes...',
        'started_at': time.time()
    })
    
    indexes = [
        # Household popup lookups (lat/lng + address)
        "CREATE INDEX IF NOT EXISTS idx_voters_coords ON voters(lat, lng) WHERE geocoded=1",
        "CREATE INDEX IF NOT EXISTS idx_voters_address ON voters(address)",
        "CREATE INDEX IF NOT EXISTS idx_voters_county_geocoded ON voters(county, geocoded)",
        
        # Election lookups
        "CREATE INDEX IF NOT EXISTS idx_ve_election_party ON voter_elections(election_date, party_voted)",
        "CREATE INDEX IF NOT EXISTS idx_ve_vuid_date ON voter_elections(vuid, election_date)",
        "CREATE INDEX IF NOT EXISTS idx_ve_date_method ON voter_elections(election_date, voting_method)",
        
        # Voter history (for flips and new voters)
        "CREATE INDEX IF NOT EXISTS idx_ve_vuid_date_party ON voter_elections(vuid, election_date, party_voted)",
        
        # Gender/age filters
        "CREATE INDEX IF NOT EXISTS idx_voters_sex ON voters(sex)",
        "CREATE INDEX IF NOT EXISTS idx_voters_birth_year ON voters(birth_year)",
        
        # County filters
        "CREATE INDEX IF NOT EXISTS idx_voters_county ON voters(county)",
    ]
    
    for idx_sql in indexes:
        try:
            conn.execute(idx_sql)
            print(f"  ✓ {idx_sql.split('idx_')[1].split(' ')[0]}")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
    
    conn.commit()
    print("Indexes added successfully\n")
    write_status({
        'stage': 'indexes',
        'status': 'completed',
        'message': f'Added {len(indexes)} indexes',
        'completed_at': time.time()
    })

def precompute_gazette(conn):
    """Pre-compute gazette insights and save to static JSON."""
    print("Pre-computing gazette insights...")
    t0 = time.time()
    write_status({
        'stage': 'gazette',
        'status': 'running',
        'message': 'Computing gazette insights...',
        'started_at': t0
    })
    
    # This is the same logic as /api/election-insights but computed once
    insights = {}
    
    # Overall turnout
    insights['ev_2022'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND voting_method='early-voting'").fetchone()[0]
    insights['ed_2022'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND voting_method='election-day'").fetchone()[0]
    insights['ev_2024'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND voting_method='early-voting'").fetchone()[0]
    insights['ed_2024'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND voting_method='election-day'").fetchone()[0]
    insights['ev_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03'").fetchone()[0]
    
    insights['total_2022'] = insights['ev_2022'] + insights['ed_2022']
    insights['total_2024'] = insights['ev_2024'] + insights['ed_2024']
    
    # Party breakdown
    insights['dem_2022'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND party_voted='Democratic'").fetchone()[0]
    insights['rep_2022'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND party_voted='Republican'").fetchone()[0]
    insights['dem_2024'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND party_voted='Democratic'").fetchone()[0]
    insights['rep_2024'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND party_voted='Republican'").fetchone()[0]
    insights['dem_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Democratic'").fetchone()[0]
    insights['rep_2026'] = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Republican'").fetchone()[0]
    
    # Party shares
    insights['dem_share_2022'] = round(insights['dem_2022'] / (insights['dem_2022'] + insights['rep_2022']) * 100, 1) if (insights['dem_2022'] + insights['rep_2022']) else 0
    insights['dem_share_2024'] = round(insights['dem_2024'] / (insights['dem_2024'] + insights['rep_2024']) * 100, 1) if (insights['dem_2024'] + insights['rep_2024']) else 0
    insights['dem_share_2026'] = round(insights['dem_2026'] / (insights['dem_2026'] + insights['rep_2026']) * 100, 1) if (insights['dem_2026'] + insights['rep_2026']) else 0
    
    # Percent of 2024 total
    insights['pct_of_2024'] = round(insights['ev_2026'] / insights['total_2024'] * 100) if insights['total_2024'] else 0
    
    # Flips for 2024 and 2026
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
    
    # New voters for 2026
    new_2026 = conn.execute("""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
          AND EXISTS (SELECT 1 FROM voter_elections ve_prior
              JOIN voters v2 ON ve_prior.vuid = v2.vuid
              WHERE v2.county = v.county AND ve_prior.election_date < '2026-03-03'
                AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
              LIMIT 1)
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    """).fetchone()[0]
    insights['new_2026'] = new_2026
    
    new_dem_2026 = conn.execute("""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03' AND ve.party_voted = 'Democratic'
          AND EXISTS (SELECT 1 FROM voter_elections ve_prior
              JOIN voters v2 ON ve_prior.vuid = v2.vuid
              WHERE v2.county = v.county AND ve_prior.election_date < '2026-03-03'
                AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
              LIMIT 1)
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    """).fetchone()[0]
    insights['new_dem_2026'] = new_dem_2026
    
    new_rep_2026 = conn.execute("""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03' AND ve.party_voted = 'Republican'
          AND EXISTS (SELECT 1 FROM voter_elections ve_prior
              JOIN voters v2 ON ve_prior.vuid = v2.vuid
              WHERE v2.county = v.county AND ve_prior.election_date < '2026-03-03'
                AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
              LIMIT 1)
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    """).fetchone()[0]
    insights['new_rep_2026'] = new_rep_2026

    # New voter age/gender breakdown
    new_age_rows = conn.execute("""
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
        WHERE ve.election_date = '2026-03-03'
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
        GROUP BY age_group, v.sex
    """).fetchall()
    
    new_age_gender_2026 = {}
    for row in new_age_rows:
        ag, sex, cnt = row[0], row[1] or 'U', row[2]
        if ag not in new_age_gender_2026:
            new_age_gender_2026[ag] = {'total': 0, 'female': 0, 'male': 0}
        new_age_gender_2026[ag]['total'] += cnt
        if sex == 'F':
            new_age_gender_2026[ag]['female'] += cnt
        elif sex == 'M':
            new_age_gender_2026[ag]['male'] += cnt
    insights['new_age_gender_2026'] = new_age_gender_2026
    
    # Gender breakdown
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
    
    # Save to cache file
    Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)
    cache_file = Path(CACHE_DIR) / 'gazette_insights.json'
    with open(cache_file, 'w') as f:
        json.dump(insights, f, separators=(',', ':'))
    
    print(f"  ✓ Gazette insights saved to {cache_file} ({time.time()-t0:.1f}s)\n")
    write_status({
        'stage': 'gazette',
        'status': 'completed',
        'message': f'Gazette cached ({time.time()-t0:.1f}s)',
        'completed_at': time.time()
    })
    return insights

def precompute_district_stats(conn):
    """Pre-compute stats for all known districts and save to cache table."""
    print("Pre-computing district stats...")
    t0 = time.time()
    write_status({
        'stage': 'districts',
        'status': 'running',
        'message': 'Computing district stats...',
        'started_at': t0
    })
    
    # Create cache table if not exists
    conn.execute("""
        CREATE TABLE IF NOT EXISTS district_stats_cache (
            district_id TEXT PRIMARY KEY,
            election_date TEXT,
            stats_json TEXT,
            computed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Get all districts with boundaries
    districts = conn.execute("""
        SELECT DISTINCT district_id, district_type
        FROM district_boundaries
        WHERE geometry IS NOT NULL
    """).fetchall()
    
    if not districts:
        print("  ⚠ No districts found in district_boundaries table\n")
        write_status({
            'stage': 'districts',
            'status': 'skipped',
            'message': 'No districts found',
            'completed_at': time.time()
        })
        return
    
    print(f"  Found {len(districts)} districts to pre-compute...")
    
    computed = 0
    for district_id, district_type in districts:
        try:
            # Get VUIDs for this district
            vuids = conn.execute("""
                SELECT DISTINCT v.vuid
                FROM voters v
                JOIN district_boundaries db ON db.district_id = ?
                WHERE v.geocoded = 1 AND v.lat IS NOT NULL AND v.lng IS NOT NULL
                  AND v.lat BETWEEN db.bbox_south AND db.bbox_north
                  AND v.lng BETWEEN db.bbox_west AND db.bbox_east
            """, (district_id,)).fetchall()
            
            if not vuids:
                continue
            
            vuid_list = [v[0] for v in vuids]
            
            # Compute stats (simplified version - full version in app.py)
            conn.execute("CREATE TEMP TABLE IF NOT EXISTS _tmp_vuids(vuid TEXT PRIMARY KEY)")
            conn.execute("DELETE FROM _tmp_vuids")
            conn.executemany("INSERT OR IGNORE INTO _tmp_vuids(vuid) VALUES(?)", [(v,) for v in vuid_list])
            
            core = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
                    SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
                FROM voter_elections ve
                INNER JOIN _tmp_vuids t ON ve.vuid = t.vuid
                WHERE ve.election_date = '2026-03-03'
            """).fetchone()
            
            stats = {
                'district_id': district_id,
                'district_type': district_type,
                'election_date': '2026-03-03',
                'total': core[0] or 0,
                'dem': core[1] or 0,
                'rep': core[2] or 0,
                'dem_share': round((core[1] or 0) / ((core[1] or 0) + (core[2] or 0)) * 100, 1) if (core[1] or 0) + (core[2] or 0) else 0,
            }
            
            # Save to cache
            conn.execute("""
                INSERT OR REPLACE INTO district_stats_cache (district_id, election_date, stats_json)
                VALUES (?, ?, ?)
            """, (district_id, '2026-03-03', json.dumps(stats)))
            
            computed += 1
            if computed % 10 == 0:
                print(f"    {computed}/{len(districts)} districts computed...")
                write_status({
                    'stage': 'districts',
                    'status': 'running',
                    'message': f'Computing district stats... {computed}/{len(districts)}',
                    'progress': computed / len(districts),
                    'started_at': t0
                })
        
        except Exception as e:
            print(f"  ✗ Failed to compute {district_id}: {e}")
    
    conn.execute("DROP TABLE IF EXISTS _tmp_vuids")
    conn.commit()
    
    print(f"  ✓ {computed} district stats cached ({time.time()-t0:.1f}s)\n")
    write_status({
        'stage': 'districts',
        'status': 'completed',
        'message': f'{computed} districts cached ({time.time()-t0:.1f}s)',
        'completed_at': time.time()
    })

def main():
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = DB_PATH
    
    print(f"Optimizing database: {db_path}\n")
    
    overall_start = time.time()
    write_status({
        'stage': 'starting',
        'status': 'running',
        'message': 'Starting optimization...',
        'started_at': overall_start
    })
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    try:
        # Step 1: Add indexes
        add_indexes(conn)
        
        # Step 2: Pre-compute gazette
        precompute_gazette(conn)
        
        # Step 3: Pre-compute district stats
        precompute_district_stats(conn)
        
        # Step 4: Analyze tables for query planner
        print("Analyzing tables for query optimizer...")
        write_status({
            'stage': 'analyze',
            'status': 'running',
            'message': 'Analyzing tables...',
            'started_at': time.time()
        })
        conn.execute("ANALYZE")
        conn.commit()
        print("  ✓ Analysis complete\n")
        
        total_time = time.time() - overall_start
        print(f"✅ All optimizations complete! ({total_time:.1f}s)")
        write_status({
            'stage': 'completed',
            'status': 'success',
            'message': f'All optimizations complete ({total_time:.1f}s)',
            'completed_at': time.time(),
            'total_time': total_time
        })
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        write_status({
            'stage': 'error',
            'status': 'failed',
            'message': str(e),
            'error': traceback.format_exc(),
            'failed_at': time.time()
        })
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
