import json
from pathlib import Path
from collections import defaultdict

data_dir = Path('/opt/whovoted/data')

# Gather all metadata + feature counts
datasets = []
for meta_path in sorted(data_dir.glob('metadata_*.json')):
    try:
        with open(meta_path) as f:
            meta = json.load(f)
        map_name = 'map_data_' + meta_path.name[len('metadata_'):]
        map_path = data_dir / map_name
        if not map_path.exists():
            continue
        with open(map_path) as f:
            geojson = json.load(f)
        features = geojson.get('features', [])
        
        # Count flips
        flips_to_dem = 0
        flips_to_rep = 0
        for feat in features:
            p = feat.get('properties', {})
            prev = p.get('party_affiliation_previous', '')
            cur = p.get('party_affiliation_current', '')
            if prev and prev != cur:
                if 'democrat' in cur.lower():
                    flips_to_dem += 1
                elif 'republican' in cur.lower():
                    flips_to_rep += 1
        
        unmatched = sum(1 for f in features if f.get('properties', {}).get('unmatched', False))
        matched = len(features) - unmatched
        
        datasets.append({
            'file': meta_path.name,
            'county': meta.get('county', ''),
            'year': meta.get('year', ''),
            'election_type': meta.get('election_type', ''),
            'election_date': meta.get('election_date', ''),
            'voting_method': meta.get('voting_method', ''),
            'primary_party': meta.get('primary_party', ''),
            'is_early_voting': meta.get('is_early_voting', False),
            'is_cumulative': meta.get('is_cumulative', False),
            'total': len(features),
            'matched': matched,
            'unmatched': unmatched,
            'flips_to_dem': flips_to_dem,
            'flips_to_rep': flips_to_rep,
        })
    except Exception as e:
        print(f"Error: {meta_path.name}: {e}")

# Print summary
print("=" * 90)
print("HIDALGO COUNTY PRIMARY ELECTION DATA SUMMARY")
print("=" * 90)

# Group by year + voting method
by_year = defaultdict(list)
for d in datasets:
    key = f"{d['year']} {d['voting_method']} {d['primary_party']}"
    by_year[(d['year'], d['voting_method'])].append(d)

for (year, method), dsets in sorted(by_year.items()):
    print(f"\n--- {year} {method.upper()} ---")
    total_all = 0
    for d in sorted(dsets, key=lambda x: x['primary_party']):
        party = d['primary_party'].upper() if d['primary_party'] else 'ALL'
        cum = " (cumulative)" if d['is_cumulative'] else ""
        flip_str = ""
        if d['flips_to_dem'] > 0 or d['flips_to_rep'] > 0:
            flip_str = f" | Flips: {d['flips_to_dem']} R→D, {d['flips_to_rep']} D→R"
        unm_str = f" | Unmatched: {d['unmatched']}" if d['unmatched'] > 0 else ""
        print(f"  {party}{cum}: {d['total']:,} voters{flip_str}{unm_str}")
        if not d['is_cumulative']:
            total_all += d['total']
    if len(dsets) > 1:
        print(f"  COMBINED: {total_all:,} total early/ED voters")

# Cross-year comparison
print("\n" + "=" * 90)
print("CROSS-YEAR EARLY VOTING COMPARISON")
print("=" * 90)

ev_by_year = {}
for d in datasets:
    if d['voting_method'] == 'early-voting' and not d['is_cumulative']:
        yr = d['year']
        if yr not in ev_by_year:
            ev_by_year[yr] = {'dem': 0, 'rep': 0, 'total': 0, 'flips_to_dem': 0, 'flips_to_rep': 0}
        if 'democrat' in d['primary_party']:
            ev_by_year[yr]['dem'] += d['total']
        elif 'republican' in d['primary_party']:
            ev_by_year[yr]['rep'] += d['total']
        ev_by_year[yr]['total'] += d['total']
        ev_by_year[yr]['flips_to_dem'] += d['flips_to_dem']
        ev_by_year[yr]['flips_to_rep'] += d['flips_to_rep']

ed_by_year = {}
for d in datasets:
    if d['voting_method'] == 'election-day':
        yr = d['year']
        if yr not in ed_by_year:
            ed_by_year[yr] = {'dem': 0, 'rep': 0, 'total': 0}
        if 'democrat' in d['primary_party']:
            ed_by_year[yr]['dem'] += d['total']
        elif 'republican' in d['primary_party']:
            ed_by_year[yr]['rep'] += d['total']
        ed_by_year[yr]['total'] += d['total']

print("\nEarly Voting Totals:")
prev_total = None
for yr in sorted(ev_by_year.keys()):
    e = ev_by_year[yr]
    dem_pct = (e['dem'] / e['total'] * 100) if e['total'] > 0 else 0
    rep_pct = (e['rep'] / e['total'] * 100) if e['total'] > 0 else 0
    change_str = ""
    if prev_total:
        change = ((e['total'] - prev_total) / prev_total) * 100
        change_str = f" ({'+' if change > 0 else ''}{change:.1f}% vs prev)"
    print(f"  {yr}: {e['total']:,} total | DEM: {e['dem']:,} ({dem_pct:.1f}%) | REP: {e['rep']:,} ({rep_pct:.1f}%){change_str}")
    if e['flips_to_dem'] > 0 or e['flips_to_rep'] > 0:
        print(f"        Flips: {e['flips_to_dem']} R→D, {e['flips_to_rep']} D→R (net {e['flips_to_dem'] - e['flips_to_rep']:+d} toward DEM)")
    prev_total = e['total']

if ed_by_year:
    print("\nElection Day Totals:")
    for yr in sorted(ed_by_year.keys()):
        e = ed_by_year[yr]
        dem_pct = (e['dem'] / e['total'] * 100) if e['total'] > 0 else 0
        rep_pct = (e['rep'] / e['total'] * 100) if e['total'] > 0 else 0
        print(f"  {yr}: {e['total']:,} total | DEM: {e['dem']:,} ({dem_pct:.1f}%) | REP: {e['rep']:,} ({rep_pct:.1f}%)")

# DEM/REP ratio analysis
print("\n" + "=" * 90)
print("DEM vs REP RATIO ANALYSIS (Early Voting)")
print("=" * 90)
for yr in sorted(ev_by_year.keys()):
    e = ev_by_year[yr]
    if e['rep'] > 0:
        ratio = e['dem'] / e['rep']
        print(f"  {yr}: {ratio:.2f} DEM for every 1 REP early voter")
    else:
        print(f"  {yr}: REP = 0")

# 2026 flip detail
print("\n" + "=" * 90)
print("2026 FLIP ANALYSIS")
print("=" * 90)
for d in datasets:
    if d['year'] == '2026' and not d['is_cumulative']:
        party = d['primary_party'].upper()
        print(f"  {party} primary: {d['flips_to_dem']} R→D flips, {d['flips_to_rep']} D→R flips out of {d['total']:,} voters")
