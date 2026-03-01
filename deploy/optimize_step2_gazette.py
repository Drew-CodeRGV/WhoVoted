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

if __name__ == '__main__':
    main()
