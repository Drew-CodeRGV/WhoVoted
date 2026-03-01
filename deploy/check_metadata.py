#!/usr/bin/env python3
"""Check metadata files to understand current state."""
import json
import glob

for f in sorted(glob.glob('/opt/whovoted/data/metadata_*.json')):
    try:
        with open(f) as fh:
            m = json.load(fh)
        print(f"=== {f.split('/')[-1]} ===")
        print(f"  voting_method: {m.get('voting_method', '?')}")
        print(f"  total: {m.get('total_addresses', 0)}")
        print(f"  is_early: {m.get('is_early_voting', False)}")
        print(f"  is_cumulative: {m.get('is_cumulative', False)}")
        print(f"  election_date: {m.get('election_date', '?')}")
    except Exception as e:
        print(f"ERROR reading {f}: {e}")
