#!/usr/bin/env python3
"""Get accurate VUID count across all sheets."""
import pandas as pd

filepath = 'WhoVoted/uploads/Hidalgo County Registered Voters.xls'

xls = pd.ExcelFile(filepath)
total_vuids = 0

for sheet in xls.sheet_names:
    df = pd.read_excel(filepath, header=None, sheet_name=sheet)
    col = df.iloc[:, 1].dropna()
    # Convert to string, strip whitespace
    col_str = col.astype(str).str.strip()
    # Match numeric values that look like VUIDs (7-10 digits, possibly with .0 suffix from float)
    col_clean = col_str.str.replace(r'\.0$', '', regex=True)
    vuids = col_clean[col_clean.str.match(r'^\d{7,10}$')]
    if len(vuids) > 0:
        print(f"Sheet '{sheet}': {len(vuids)} VUIDs (sample: {vuids.iloc[0]})")
    else:
        # Show what's actually in column 1
        samples = col_str.head(3).tolist()
        print(f"Sheet '{sheet}': 0 VUIDs (samples: {samples})")
    total_vuids += len(vuids)

print(f"\nTotal VUIDs: {total_vuids}")
