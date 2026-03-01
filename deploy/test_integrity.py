#!/usr/bin/env python3
"""Test the integrity checker on current deployed datasets."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')

import json
from pathlib import Path
from integrity import verify_ev_upload

DATA_DIR = Path('/opt/whovoted/data')
PUBLIC_DIR = Path('/opt/whovoted/public')
DB_PATH = str(DATA_DIR / 'whovoted.db')

for party, raw_count in [('democratic', 31905), ('republican', 7719)]:
    print(f"\n{'='*60}")
    print(f"  {party.upper()} INTEGRITY CHECK")
    print(f"{'='*60}")
    
    party_suffix = f'_{party}'
    
    # Try snapshot first, fall back to cumulative for feature count
    norm_count = 0
    snap_file = DATA_DIR / f'map_data_Hidalgo_2026_primary{party_suffix}_20260303_ev.json'
    cum_file = DATA_DIR / f'map_data_Hidalgo_2026_primary{party_suffix}_cumulative_ev.json'
    
    for gf in [snap_file, cum_file]:
        if gf.exists():
            with open(gf) as f:
                data = json.load(f)
            norm_count = len(data.get('features', []))
            print(f"  Using {gf.name}: {norm_count} features")
            break
    
    # Read metadata for geocoded/unmatched
    geocoded = 0
    unmatched = 0
    for mf_name in [
        f'metadata_Hidalgo_2026_primary{party_suffix}_20260303_ev.json',
        f'metadata_Hidalgo_2026_primary{party_suffix}_cumulative_ev.json',
    ]:
        mf = DATA_DIR / mf_name
        if mf.exists():
            with open(mf) as f:
                meta = json.load(f)
            geocoded = meta.get('matched_vuids', 0)
            unmatched = meta.get('unmatched_vuids', 0)
            break
    
    report = verify_ev_upload(
        db_path=DB_PATH,
        data_dir=DATA_DIR,
        public_dir=PUBLIC_DIR,
        county='Hidalgo',
        year='2026',
        election_type='primary',
        election_date='2026-03-03',
        party=party,
        raw_row_count=raw_count,
        cleaned_row_count=norm_count,
        normalized_vuid_count=norm_count,
        geocoded_count=geocoded,
        unmatched_count=unmatched,
        job_id='test',
        source_file='test',
    )
    
    for line in report.summary_lines():
        print(f"  {line}")
    
    if report.passed:
        print(f"\n  ✅ ALL CHECKS PASSED")
    else:
        print(f"\n  ❌ {len(report.failed_checks)} CHECK(S) FAILED:")
        for c in report.failed_checks:
            print(f"    - {c['name']}: expected={c['expected']}, actual={c['actual']}")
            if c['detail']:
                print(f"      {c['detail']}")
