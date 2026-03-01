import json
from pathlib import Path

data_dir = Path('/opt/whovoted/data')
for f in sorted(data_dir.glob('metadata_*.json')):
    with open(f) as fh:
        m = json.load(fh)
    yr = m.get('year', '?')
    party = m.get('primary_party', '?')
    method = m.get('voting_method', '?')
    total = m.get('total_addresses', 0)
    ev = m.get('is_early_voting', False)
    cum = m.get('is_cumulative', False)
    print(f"{yr} {party:12s} {method:15s} ev={ev} cum={cum} | {total:>6} voters | {f.name}")
