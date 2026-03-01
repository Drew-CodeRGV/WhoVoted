#!/usr/bin/env python3
"""Quick check of EVR scraper state."""
import json
state = json.load(open('/opt/whovoted/data/evr_scraper_state.json'))
processed = state.get('processed', {})
print(f"{len(processed)} dates processed so far")
for k in sorted(processed.keys()):
    info = processed[k]
    print(f"  {k}: {info.get('unique', '?')} unique records")
