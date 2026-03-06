#!/usr/bin/env python3
"""Regenerate TX-15 cache with timestamp and show ALL counties."""

import sqlite3
import json
from pathlib import Path
from collections import defaultdict
from datetime import datetime

CACHE_DIR = '/opt/whovoted/public/cache'
Path(CACHE_DIR).mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
conn.row_factory = sqlite3.Row

print("=" * 70)
print("Regenerating TX-15 Congressional District Cache")
print("=" * 70)

# Get TX-15 voters with corrected county assignments
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
    WHERE v.congressional_district = '15'
    AND ve.election_date = '2026-03-03'
""").fetchall()

print(f"Found {len(voters):,} voters in TX-15")

# Calculate stats
total = len(voters)
dem = sum(1 for v in voters if 'democrat' in (v['party_voted'] or '').lower())
rep = sum(1 for v in voters if 'republican' in (v['party_voted'] or '').lower())

# By county - SHOW ALL COUNTIES, don't hide any
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

# Build report with timestamp
report = {
    'district_id': 'TX-15',
    'district_name': 'TX-15 Congressional District (PlanC2333)',
    'district_type': 'congressional',
    'election_date': '2026-03-03',
    'generated_at': datetime.now().isoformat(),
    'generated_timestamp': int(datetime.now().timestamp()),
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
safe_name = 'TX-15_Congressional_District_(PlanC2333)'.replace(' ', '_').replace('/', '_')
cache_file = Path(CACHE_DIR) / f'district_report_{safe_name}.json'
with open(cache_file, 'w') as f:
    json.dump(report, f, separators=(',', ':'))

print(f"\n✓ Cached TX-15 report:")
print(f"  Total: {total:,} voters")
print(f"  Dem: {dem:,} ({dem/total*100:.1f}%)")
print(f"  Rep: {rep:,} ({rep/total*100:.1f}%)")
print(f"  Generated at: {report['generated_at']}")
print(f"\n  Counties (ALL shown, none hidden):")
for item in report['votes_by_county']:
    print(f"    {item['county']:20s}: {item['total']:6,} voters (D:{item['dem']:5,} R:{item['rep']:5,})")

print(f"\n✓ Saved to: {cache_file}")

conn.close()

print(f"\n{'=' * 70}")
print("CACHE REGENERATED WITH TIMESTAMP")
print(f"{'=' * 70}")
