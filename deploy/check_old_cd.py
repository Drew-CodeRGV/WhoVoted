#!/usr/bin/env python3
import json
d = json.load(open('/opt/whovoted/public/data/districts_old_congressional.json'))
print(f"Old congressional features: {len(d['features'])}")
for f in d['features']:
    print(f"  {f['properties'].get('district_id', 'unknown')}")
