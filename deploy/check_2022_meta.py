import json
from pathlib import Path

data_dir = Path('/opt/whovoted/data')
for f in sorted(data_dir.glob('metadata_*2022*')):
    with open(f) as fh:
        m = json.load(fh)
    print(f"\n{f.name}:")
    for k, v in m.items():
        print(f"  {k}: {v}")
