#!/usr/bin/env python3
"""Check if combined datasets are being created correctly."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.database import get_db, cache_clear
import json

# Clear cache
cache_clear('elections:Hidalgo')
print("Cache cleared for elections:Hidalgo")

# Get datasets
db = get_db()
datasets = db.get_election_datasets('Hidalgo')

print(f"\nFound {len(datasets)} raw datasets from DB:")
for ds in datasets:
    print(f"  {ds['election_date']} | {ds['voting_method']:15} | {ds['party_voted']:12} | {ds['total_voters']:6} voters")

# Group by election_date to see what should be combined
from collections import defaultdict
by_date = defaultdict(list)
for ds in datasets:
    by_date[ds['election_date']].append(ds)

print(f"\nGrouped by election date:")
for date, dss in sorted(by_date.items(), reverse=True):
    methods = set(ds['voting_method'] for ds in dss)
    total = sum(ds['total_voters'] for ds in dss)
    print(f"  {date}: {len(methods)} methods ({', '.join(sorted(methods))}) = {total:,} total voters")
    if len(methods) > 1:
        print(f"    ✓ Should create combined dataset")
    else:
        print(f"    ✗ Only one method, no combined dataset")
