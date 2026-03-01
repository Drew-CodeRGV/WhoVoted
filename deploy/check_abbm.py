#!/usr/bin/env python3
"""Check the ABBM file columns and sample data."""
import glob
import pandas as pd

uploads = glob.glob('/opt/whovoted/uploads/*ABBM*')
for f in uploads:
    print(f"\n{'='*80}")
    print(f"FILE: {f.split('/')[-1]}")
    print(f"{'='*80}")
    try:
        df = pd.read_excel(f)
        print(f"Shape: {df.shape}")
        print(f"Columns: {list(df.columns)}")
        print(f"\nFirst 3 rows:")
        print(df.head(3).to_string())
        print(f"\nColumn dtypes:")
        print(df.dtypes)
    except Exception as e:
        print(f"Error reading: {e}")
