#!/usr/bin/env python3
import json
with open('/opt/whovoted/public/data/map_data_Hidalgo_2026_primary_democratic_cumulative_ev.json') as f:
    data = json.load(f)
# Check first 5 voters
for feat in data['features'][:5]:
    p = feat['properties']
    print(f"  {p['name']}: sex={p.get('sex','MISSING')}, party={p['party_affiliation_current']}")

# Count sex distribution
from collections import Counter
sexes = Counter(f['properties'].get('sex', '') for f in data['features'])
print(f"\nSex distribution in DEM cumulative: {dict(sexes)}")
