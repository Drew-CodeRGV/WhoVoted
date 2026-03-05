#!/usr/bin/env python3
"""
Regenerate all district caches with corrected first-time voter logic
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')

import database as db
import json
from pathlib import Path
from datetime import datetime

def generate_district_stats(conn, district_type, district_id, election_date):
    """Generate stats for a single district using is_new_voter flag"""
    
    # Map district type to column name
    column_map = {
        'congressional': 'congressional_district',
        'state_house': 'state_house_district',
        'commissioner': 'commissioner_district'
    }
    
    district_column = column_map.get(district_type)
    if not district_column:
        return None
    
    # Create temp table with district voters
    conn.execute("DROP TABLE IF EXISTS _ds_vuids")
    conn.execute(f"""
        CREATE TEMP TABLE _ds_vuids AS
        SELECT DISTINCT v.vuid
        FROM voters v
        WHERE v.{district_column} = ?
    """, [district_id])
    
    # Total turnout
    total_row = conn.execute("""
        SELECT COUNT(*) as total,
               SUM(CASE WHEN party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
               SUM(CASE WHEN party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
        FROM voter_elections ve
        INNER JOIN _ds_vuids t ON ve.vuid = t.vuid
        WHERE ve.election_date = ?
    """, [election_date]).fetchone()
    
    total = total_row['total'] or 0
    dem = total_row['dem'] or 0
    rep = total_row['rep'] or 0
    
    # New voters using is_new_voter flag
    new_row = conn.execute("""
        SELECT COUNT(*) as new_total,
               SUM(CASE WHEN party_voted = 'Democratic' THEN 1 ELSE 0 END) as new_dem,
               SUM(CASE WHEN party_voted = 'Republican' THEN 1 ELSE 0 END) as new_rep
        FROM voter_elections ve
        INNER JOIN _ds_vuids t ON ve.vuid = t.vuid
        WHERE ve.election_date = ? AND ve.is_new_voter = 1
    """, [election_date]).fetchone()
    
    new_total = new_row['new_total'] or 0
    new_dem = new_row['new_dem'] or 0
    new_rep = new_row['new_rep'] or 0
    
    # Flips
    flip_rows = conn.execute("""
        SELECT ve_cur.party_voted as to_p, ve_prev.party_voted as from_p, COUNT(*) as cnt
        FROM voter_elections ve_cur
        INNER JOIN _ds_vuids t ON ve_cur.vuid = t.vuid
        INNER JOIN voter_elections ve_prev ON ve_cur.vuid = ve_prev.vuid
        WHERE ve_cur.election_date = ?
          AND ve_prev.election_date = (
              SELECT MAX(ve2.election_date) FROM voter_elections ve2
              WHERE ve2.vuid = ve_cur.vuid AND ve2.election_date < ?
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
          AND ve_cur.party_voted != ve_prev.party_voted
          AND ve_cur.party_voted != '' AND ve_prev.party_voted != ''
        GROUP BY ve_cur.party_voted, ve_prev.party_voted
    """, [election_date, election_date]).fetchall()
    
    r2d = sum(r['cnt'] for r in flip_rows if r['from_p'] == 'Republican' and r['to_p'] == 'Democratic')
    d2r = sum(r['cnt'] for r in flip_rows if r['from_p'] == 'Democratic' and r['to_p'] == 'Republican')
    
    # Gender
    gender_row = conn.execute("""
        SELECT SUM(CASE WHEN v.sex = 'F' THEN 1 ELSE 0 END) as female,
               SUM(CASE WHEN v.sex = 'M' THEN 1 ELSE 0 END) as male
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        INNER JOIN _ds_vuids t ON ve.vuid = t.vuid
        WHERE ve.election_date = ?
    """, [election_date]).fetchone()
    
    female = gender_row['female'] or 0
    male = gender_row['male'] or 0
    
    return {
        'district_type': district_type,
        'district_id': district_id,
        'election_date': election_date,
        'total': total,
        'dem': dem,
        'rep': rep,
        'new_total': new_total,
        'new_dem': new_dem,
        'new_rep': new_rep,
        'r2d': r2d,
        'd2r': d2r,
        'female': female,
        'male': male,
        'generated_at': datetime.utcnow().isoformat()
    }

def main():
    conn = db.get_connection()
    cache_dir = Path('/opt/whovoted/public/cache')
    cache_dir.mkdir(exist_ok=True)
    
    election_date = '2026-03-03'
    
    # Get all districts
    districts = []
    
    # Congressional districts
    cong_rows = conn.execute("""
        SELECT DISTINCT congressional_district 
        FROM voters 
        WHERE congressional_district IS NOT NULL AND congressional_district != ''
    """).fetchall()
    for row in cong_rows:
        districts.append(('congressional', row[0]))
    
    # State house districts
    house_rows = conn.execute("""
        SELECT DISTINCT state_house_district 
        FROM voters 
        WHERE state_house_district IS NOT NULL AND state_house_district != ''
    """).fetchall()
    for row in house_rows:
        districts.append(('state_house', row[0]))
    
    # Commissioner districts (county-specific)
    comm_rows = conn.execute("""
        SELECT DISTINCT commissioner_district 
        FROM voters 
        WHERE commissioner_district IS NOT NULL AND commissioner_district != ''
    """).fetchall()
    for row in comm_rows:
        districts.append(('commissioner', row[0]))
    
    print(f"Found {len(districts)} districts to process")
    
    # Generate cache for each district
    for i, (dtype, did) in enumerate(districts, 1):
        print(f"[{i}/{len(districts)}] Processing {dtype} {did}...")
        
        stats = generate_district_stats(conn, dtype, did, election_date)
        if stats:
            cache_file = cache_dir / f"district_stats_{dtype}_{did}_{election_date}.json"
            with open(cache_file, 'w') as f:
                json.dump(stats, f, indent=2)
            print(f"  ✓ Cached: {cache_file.name}")
            print(f"    Total: {stats['total']}, New: {stats['new_total']} ({stats['new_total']/stats['total']*100:.1f}%)")
    
    print(f"\n✓ Regenerated {len(districts)} district caches")

if __name__ == '__main__':
    main()
