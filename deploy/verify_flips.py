import json
from pathlib import Path

data_dir = Path('/opt/whovoted/data')

for meta_path in sorted(data_dir.glob('metadata_*.json')):
    with open(meta_path) as f:
        meta = json.load(f)
    
    map_name = 'map_data_' + meta_path.name[len('metadata_'):]
    map_path = data_dir / map_name
    if not map_path.exists():
        continue
    
    with open(map_path) as f:
        geojson = json.load(f)
    
    features = geojson.get('features', [])
    flips = sum(1 for f in features 
                if f['properties'].get('party_affiliation_previous', '') 
                and f['properties']['party_affiliation_previous'] != f['properties'].get('party_affiliation_current', ''))
    
    year = meta.get('year', '?')
    party = meta.get('primary_party', '?')
    method = meta.get('voting_method', '?')
    edate = meta.get('election_date', '?')
    
    print(f"{year} {party} {method} (date={edate}): {len(features)} voters, {flips} flips")
