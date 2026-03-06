#!/usr/bin/env python3
"""Regenerate cache files for TX-15, TX-28, and TX-34 with corrected assignments."""

import sqlite3
import json
from pathlib import Path
from collections import defaultdict

CACHE_DIR = '/opt/whovoted/public/cache'
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row

DISTRICTS = [
    ('15', 'TX-15 Congressional District (PlanC2333)'),
    ('28', 'TX-28 Congressional District (PlanC2333)'),
    ('34', 'TX-34 Congressional District (PlanC2333)')
]

for district_num, district_name in DISTRICTS:
    print(f"\n{'=' * 70}")
    print(f"Regenerating {district_name}")
    print(f"{'=' * 70}")
    
    # Get voters with corrected assignments
    voters = conn.execute("""
        SELECT 
            v.vuid,
            v.county,
            ve.party_voted,
            ve.voting_method,
            v.sex,
            v.birth_year,
            ve.is_new_voter
        FROM voters v
        JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.congressional_district = ?
        AND ve.election_date = '2026-03-03'
    """, [district_num]).fetchall()
    
    print(f"Found {len(voters):,} voters in TX-{district_num}")
    
    # Calculate stats
    total = len(voters)
    if total == 0:
        print(f"WARNING: No voters found for TX-{district_num}!")
        continue
    
    dem = sum(1 for v in voters if 'democrat' in (v['party_voted'] or '').lower())
    rep = sum(1 for v in voters if 'republican' in (v['party_voted'] or '').lower())
    
    # By county
    by_county = defaultdict(lambda: {'total': 0, 'dem': 0, 'rep': 0})
    for v in voters:
        county = v['county'] or 'Unknown'
        by_county[county]['total'] += 1
        if 'democrat' in (v['party_voted'] or '').lower():
            by_county[county]['dem'] += 1
        elif 'republican' in (v['party_voted'] or '').lower():
            by_county[county]['rep'] += 1
    
    # By gender
    male = sum(1 for v in voters if v['sex'] == 'M')
    female = sum(1 for v in voters if v['sex'] == 'F')
    
    # By age
    current_year = 2026
    age_groups = defaultdict(int)
    for v in voters:
        if v['birth_year']:
            age = current_year - v['birth_year']
            if age < 25:
                age_groups['18-24'] += 1
            elif age < 35:
                age_groups['25-34'] += 1
            elif age < 45:
                age_groups['35-44'] += 1
            elif age < 55:
                age_groups['45-54'] += 1
            elif age < 65:
                age_groups['55-64'] += 1
            elif age < 75:
                age_groups['65-74'] += 1
            else:
                age_groups['75+'] += 1
    
    # New voters
    new_voters = sum(1 for v in voters if v['is_new_voter'])
    
    # Build report
    report = {
        'district_id': f'TX-{district_num}',
        'district_name': district_name,
        'district_type': 'congressional',
        'election_date': '2026-03-03',
        'total': total,
        'dem': dem,
        'rep': rep,
        'male': male,
        'female': female,
        'age_groups': dict(age_groups),
        'new_total': new_voters,
        'votes_by_county': [
            {
                'county': county,
                'total': data['total'],
                'dem': data['dem'],
                'rep': data['rep']
            }
            for county, data in sorted(by_county.items(), key=lambda x: x[1]['total'], reverse=True)
        ]
    }
    
    # Save cache file
    safe_name = district_name.replace(' ', '_').replace('/', '_')
    cache_file = Path(CACHE_DIR) / f'district_report_{safe_name}.json'
    with open(cache_file, 'w') as f:
        json.dump(report, f, separators=(',', ':'))
    
    print(f"\n✓ Cached TX-{district_num} report:")
    print(f"  Total: {total:,} voters")
    print(f"  Dem: {dem:,} ({dem/total*100:.1f}%)")
    print(f"  Rep: {rep:,} ({rep/total*100:.1f}%)")
    print(f"\n  Top 5 counties:")
    for item in report['votes_by_county'][:5]:
        print(f"    {item['county']:20s}: {item['total']:6,} voters (D:{item['dem']:5,} R:{item['rep']:5,})")
    
    print(f"\n✓ Saved to: {cache_file}")

conn.close()

print(f"\n{'=' * 70}")
print("ALL DISTRICT CACHES REGENERATED")
print(f"{'=' * 70}")
