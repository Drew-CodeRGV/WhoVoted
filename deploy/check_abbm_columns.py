#!/usr/bin/env python3
"""Check ABBM file columns and sample data."""
import pandas as pd
import os

upload_dir = '/opt/whovoted/uploads'
for f in sorted(os.listdir(upload_dir)):
    if 'ABBM' in f or 'abbm' in f:
        path = os.path.join(upload_dir, f)
        print(f"\n{'='*60}")
        print(f"File: {f}")
        print(f"{'='*60}")
        
        df = pd.read_excel(path)
        print(f"Columns: {list(df.columns)}")
        print(f"Rows: {len(df)}")
        print(f"\nFirst 3 rows:")
        print(df.head(3).to_string())
        print(f"\nColumn dtypes:")
        print(df.dtypes)
