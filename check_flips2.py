import json, os
from pathlib import Path

data_dir = Path('/opt/whovoted/data')

# Check all metadata files
print("=== All metadata files ===")
for f in sorted(data_dir.glob('metadata_*.json')):
    with open(f) as fh:
        meta = json.load(fh)
    county = meta.get('county', '')
    edate = meta.get('election_date', '')
    party = meta.get('primary_party', '')
    year = meta.get('year', '')
    print(f"  {f.name}: county={county}, date={edate}, year={year}, party={party}")

print()

# Simulate what find_earlier_datasets would do for 2026 data
# The 2026 metadata has election_date = "2026-02-23"
current_date = "2026-02-23"
county = "Hidalgo"

print(f"=== Earlier datasets for county={county}, date<{current_date} ===")
for f in sorted(data_dir.glob('metadata_*.json')):
    with open(f) as fh:
        meta = json.load(fh)
    mc = meta.get('county', '')
    ed = meta.get('election_date', '')
    if mc.lower() == county.lower() and ed and ed < current_date:
        map_name = 'map_data_' + f.name[len('metadata_'):]
        map_path = data_dir / map_name
        exists = map_path.exists()
        print(f"  MATCH: {f.name} -> date={ed}, map_data exists={exists}")

print()

# Now check: does the 2026 processing code path even call cross_reference?
# Check the actual 2026 REP data more carefully
with open(data_dir / 'map_data_Hidalgo_2026_primary_republican_20260223.json') as f:
    data = json.load(f)

features = data.get('features', [])
# Count how many have non-empty party_affiliation_previous
has_prev = sum(1 for feat in features if feat.get('properties', {}).get('party_affiliation_previous', ''))
print(f"2026 REP: {len(features)} total, {has_prev} with party_affiliation_previous set")

# Check has_switched_parties
switched = sum(1 for feat in features if feat.get('properties', {}).get('has_switched_parties'))
print(f"2026 REP: {switched} with has_switched_parties=True")

# Check a few samples
for feat in features[:5]:
    p = feat['properties']
    print(f"  VUID={p.get('vuid','?')}, current={p.get('party_affiliation_current','')}, prev={p.get('party_affiliation_previous','')}, switched={p.get('has_switched_parties','')}")

print()

# Same for DEM
with open(data_dir / 'map_data_Hidalgo_2026_primary_democratic_20260223.json') as f:
    data = json.load(f)

features = data.get('features', [])
has_prev = sum(1 for feat in features if feat.get('properties', {}).get('party_affiliation_previous', ''))
switched = sum(1 for feat in features if feat.get('properties', {}).get('has_switched_parties'))
print(f"2026 DEM: {len(features)} total, {has_prev} with party_affiliation_previous, {switched} switched")

for feat in features[:5]:
    p = feat['properties']
    print(f"  VUID={p.get('vuid','?')}, current={p.get('party_affiliation_current','')}, prev={p.get('party_affiliation_previous','')}, switched={p.get('has_switched_parties','')}")
