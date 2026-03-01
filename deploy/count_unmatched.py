import json
from pathlib import Path

data_dir = Path('/opt/whovoted/data')

for filepath in sorted(data_dir.glob('map_data_*.json')):
    try:
        with open(filepath) as f:
            data = json.load(f)
        features = data.get('features', [])
        unmatched = sum(1 for f in features if f.get('properties', {}).get('unmatched', False))
        total = len(features)
        if unmatched > 0 or 'cumulative' in filepath.name or '2026' in filepath.name:
            print(f"{filepath.name}: {total} total, {unmatched} unmatched")
    except Exception as e:
        print(f"{filepath.name}: ERROR {e}")
