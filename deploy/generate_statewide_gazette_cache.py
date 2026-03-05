#!/usr/bin/env python3
"""
Generate statewide gazette cache with fun statistics.
Only 2026 data, no historical comparisons.
"""
import sqlite3
import json
from pathlib import Path
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_FILE = '/opt/whovoted/public/cache/gazette_insights.json'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("Generating statewide gazette cache...")

# Overall 2026 turnout
overall = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as total,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep,
        SUM(CASE WHEN ve.voting_method = 'early-voting' THEN 1 ELSE 0 END) as early_voting,
        SUM(CASE WHEN ve.voting_method = 'mail-in' THEN 1 ELSE 0 END) as mail_in,
        SUM(CASE WHEN ve.voting_method = 'election-day' THEN 1 ELSE 0 END) as election_day
    FROM voter_elections ve
    WHERE ve.election_date = '2026-03-03'
      AND ve.party_voted IN ('Democratic', 'Republican')
""").fetchone()

# Gender breakdown
gender = conn.execute("""
    SELECT 
        SUM(CASE WHEN v.sex = 'F' THEN 1 ELSE 0 END) as female,
        SUM(CASE WHEN v.sex = 'M' THEN 1 ELSE 0 END) as male,
        SUM(CASE WHEN ve.party_voted = 'Democratic' AND v.sex = 'F' THEN 1 ELSE 0 END) as dem_female,
        SUM(CASE WHEN ve.party_voted = 'Democratic' AND v.sex = 'M' THEN 1 ELSE 0 END) as dem_male,
        SUM(CASE WHEN ve.party_voted = 'Republican' AND v.sex = 'F' THEN 1 ELSE 0 END) as rep_female,
        SUM(CASE WHEN ve.party_voted = 'Republican' AND v.sex = 'M' THEN 1 ELSE 0 END) as rep_male
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND ve.party_voted IN ('Democratic', 'Republican')
""").fetchone()

# Age groups
age_groups = {}
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
        ve.party_voted,
        COUNT(*) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND ve.party_voted IN ('Democratic', 'Republican')
    GROUP BY age_group, ve.party_voted
""").fetchall()

for row in age_rows:
    ag = row['age_group']
    if ag not in age_groups:
        age_groups[ag] = {'total': 0, 'dem': 0, 'rep': 0}
    age_groups[ag]['total'] += row['cnt']
    if row['party_voted'] == 'Democratic':
        age_groups[ag]['dem'] += row['cnt']
    else:
        age_groups[ag]['rep'] += row['cnt']

# Top 10 counties by turnout
top_counties = conn.execute("""
    SELECT 
        v.county,
        COUNT(DISTINCT ve.vuid) as total,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND ve.party_voted IN ('Democratic', 'Republican')
      AND v.county IS NOT NULL
      AND v.county != ''
    GROUP BY v.county
    ORDER BY total DESC
    LIMIT 10
""").fetchall()

# Bottom 10 counties by turnout
bottom_counties = conn.execute("""
    SELECT 
        v.county,
        COUNT(DISTINCT ve.vuid) as total,
        SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
        SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND ve.party_voted IN ('Democratic', 'Republican')
      AND v.county IS NOT NULL
      AND v.county != ''
    GROUP BY v.county
    ORDER BY total ASC
    LIMIT 10
""").fetchall()

# Party switchers
flips = conn.execute("""
    SELECT 
        ve_cur.party_voted as to_party,
        ve_prev.party_voted as from_party,
        COUNT(*) as cnt
    FROM voter_elections ve_cur
    JOIN voter_elections ve_prev ON ve_cur.vuid = ve_prev.vuid
    WHERE ve_cur.election_date = '2026-03-03'
      AND ve_prev.election_date = (
          SELECT MAX(ve2.election_date) 
          FROM voter_elections ve2
          WHERE ve2.vuid = ve_cur.vuid 
            AND ve2.election_date < '2026-03-03'
            AND ve2.party_voted IN ('Democratic', 'Republican')
      )
      AND ve_cur.party_voted != ve_prev.party_voted
      AND ve_cur.party_voted IN ('Democratic', 'Republican')
      AND ve_prev.party_voted IN ('Democratic', 'Republican')
    GROUP BY ve_cur.party_voted, ve_prev.party_voted
""").fetchall()

r2d = sum(r['cnt'] for r in flips if r['from_party'] == 'Republican' and r['to_party'] == 'Democratic')
d2r = sum(r['cnt'] for r in flips if r['from_party'] == 'Democratic' and r['to_party'] == 'Republican')

# Build cache object
cache = {
    'generated_at': datetime.now().isoformat(),
    'election_date': '2026-03-03',
    
    # Overall stats
    'total': overall['total'],
    'dem': overall['dem'],
    'rep': overall['rep'],
    'dem_share': round(overall['dem'] / overall['total'] * 100, 1) if overall['total'] > 0 else 0,
    'early_voting': overall['early_voting'],
    'mail_in': overall['mail_in'],
    'election_day': overall['election_day'],
    
    # Gender
    'female': gender['female'],
    'male': gender['male'],
    'dem_female': gender['dem_female'],
    'dem_male': gender['dem_male'],
    'rep_female': gender['rep_female'],
    'rep_male': gender['rep_male'],
    
    # Age groups
    'age_groups': age_groups,
    
    # Party switchers
    'r2d': r2d,
    'd2r': d2r,
    
    # Top/bottom counties
    'top_counties': [
        {
            'county': r['county'],
            'total': r['total'],
            'dem': r['dem'],
            'rep': r['rep'],
            'dem_pct': round(r['dem'] / r['total'] * 100, 1) if r['total'] > 0 else 0
        }
        for r in top_counties
    ],
    'bottom_counties': [
        {
            'county': r['county'],
            'total': r['total'],
            'dem': r['dem'],
            'rep': r['rep'],
            'dem_pct': round(r['dem'] / r['total'] * 100, 1) if r['total'] > 0 else 0
        }
        for r in bottom_counties
    ]
}

# Save cache
Path(CACHE_FILE).parent.mkdir(parents=True, exist_ok=True)
with open(CACHE_FILE, 'w') as f:
    json.dump(cache, f, indent=2)

print(f"✅ Cache generated: {CACHE_FILE}")
print(f"   Total voters: {cache['total']:,}")
print(f"   Democratic: {cache['dem']:,} ({cache['dem_share']}%)")
print(f"   Republican: {cache['rep']:,}")
print(f"   Top county: {cache['top_counties'][0]['county']} ({cache['top_counties'][0]['total']:,} voters)")

conn.close()
