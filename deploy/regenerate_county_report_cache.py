#!/usr/bin/env python3
"""Regenerate county report cache files."""

import sys
import os
sys.path.insert(0, '/opt/whovoted/backend')

import json
from pathlib import Path
import database as db

def generate_county_report(county, election_date, voting_method=''):
    """Generate county report data."""
    conn = db.get_connection()
    
    # Build WHERE clause
    where_base = "WHERE v.county = ? AND ve.election_date = ?"
    params_base = [county, election_date]
    if voting_method:
        where_base += " AND ve.voting_method = ?"
        params_base.append(voting_method)
    
    # Total voters
    total_voters = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base}
    """, params_base).fetchone()[0]
    
    # Party breakdown
    dem_count = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND ve.party_voted = 'Democratic'
    """, params_base).fetchone()[0]
    
    rep_count = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND ve.party_voted = 'Republican'
    """, params_base).fetchone()[0]
    
    # Party switchers
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
    
    r2d = sum(r[2] for r in flip_rows if r[1] == 'Republican' and r[0] == 'Democratic')
    d2r = sum(r[2] for r in flip_rows if r[1] == 'Democratic' and r[0] == 'Republican')
    
    # New voters
    new_voters = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base}
          AND EXISTS (SELECT 1 FROM voter_elections ve_prior
              JOIN voters v2 ON ve_prior.vuid = v2.vuid
              WHERE v2.county = v.county AND ve_prior.election_date < ?
                AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
              LIMIT 1)
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    """, params_base + [election_date, election_date]).fetchone()[0]
    
    new_dem = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND ve.party_voted = 'Democratic'
          AND EXISTS (SELECT 1 FROM voter_elections ve_prior
              JOIN voters v2 ON ve_prior.vuid = v2.vuid
              WHERE v2.county = v.county AND ve_prior.election_date < ?
                AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
              LIMIT 1)
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    """, params_base + [election_date, election_date]).fetchone()[0]
    
    new_rep = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND ve.party_voted = 'Republican'
          AND EXISTS (SELECT 1 FROM voter_elections ve_prior
              JOIN voters v2 ON ve_prior.vuid = v2.vuid
              WHERE v2.county = v.county AND ve_prior.election_date < ?
                AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
              LIMIT 1)
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    """, params_base + [election_date, election_date]).fetchone()[0]
    
    # Gender
    female_count = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND v.sex = 'F'
    """, params_base).fetchone()[0]
    
    male_count = conn.execute(f"""
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
            ve.party_voted,
            COUNT(*) as cnt
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
    
    # Calculate percentages
    dem_share = round(dem_count / (dem_count + rep_count) * 100, 1) if (dem_count + rep_count) else 0
    new_dem_pct = round(new_dem / new_voters * 100, 1) if new_voters else 0
    female_pct = round(female_count / (female_count + male_count) * 100, 1) if (female_count + male_count) else 0
    
    return {
        'county': county,
        'election_date': election_date,
        'voting_method': voting_method or 'all',
        'total_voters': total_voters,
        'dem_count': dem_count,
        'rep_count': rep_count,
        'dem_share': dem_share,
        'r2d': r2d,
        'd2r': d2r,
        'new_voters': new_voters,
        'new_dem': new_dem,
        'new_rep': new_rep,
        'new_dem_pct': new_dem_pct,
        'female_count': female_count,
        'male_count': male_count,
        'female_pct': female_pct,
        'age_groups': age_groups,
        'last_updated': election_date
    }

def main():
    # Get all counties with 2026-03-03 data
    conn = db.get_connection()
    counties_with_data = conn.execute("""
        SELECT DISTINCT v.county, ve.voting_method, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        GROUP BY v.county, ve.voting_method
        HAVING cnt > 0
        ORDER BY v.county, ve.voting_method
    """).fetchall()
    
    print(f"Found {len(counties_with_data)} county/method combinations")
    
    cache_dir = Path('/opt/whovoted/public/cache')
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    election_date = '2026-03-03'
    
    for row in counties_with_data:
        county = row[0]
        voting_method = row[1]
        count = row[2]
        
        print(f"\nGenerating {county} {election_date} {voting_method} ({count} voters)...")
        try:
            data = generate_county_report(county, election_date, voting_method)
            
            cache_file = cache_dir / f'county_report_{county}_{election_date}_{voting_method}.json'
            with open(cache_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"  ✓ Saved to {cache_file}")
            print(f"  Total: {data['total_voters']}, Age groups: {len(data['age_groups'])}")
        except Exception as e:
            print(f"  ✗ Error: {e}")

if __name__ == '__main__':
    main()
