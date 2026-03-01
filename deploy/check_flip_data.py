#!/usr/bin/env python3
"""Check flip data in the deployed GeoJSON files."""
import json

for party in ['democratic', 'republican']:
    path = f'/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_{party}_cumulative_ev.json'
    try:
        with open(path) as f:
            data = json.load(f)
        
        total = len(data['features'])
        flipped = 0
        flip_details = {}
        
        for f in data['features']:
            p = f.get('properties', {})
            if p.get('has_switched_parties'):
                flipped += 1
                cur = p.get('party_affiliation_current', '')
                prev = p.get('party_affiliation_previous', '')
                key = f"{prev} -> {cur}"
                flip_details[key] = flip_details.get(key, 0) + 1
        
        print(f"\n{party.upper()}: {total} total, {flipped} flipped")
        for k, v in sorted(flip_details.items(), key=lambda x: -x[1]):
            print(f"  {k}: {v}")
            
        # Show a few examples
        examples = [f for f in data['features'] if f['properties'].get('has_switched_parties')][:3]
        for ex in examples:
            p = ex['properties']
            print(f"  Example: VUID={p.get('vuid')}, cur={p.get('party_affiliation_current')}, prev={p.get('party_affiliation_previous')}")
    except Exception as e:
        print(f"{party.upper()}: ERROR - {e}")
