#!/usr/bin/env python3
import pandas as pd

file_path = '/opt/whovoted/data/district_reference/PLANC2333_r110_VTD24G.xls'

# Read without headers
df = pd.read_excel(file_path, sheet_name=0, header=None)

print("File shape:", df.shape)
print("\nFirst 50 rows, first 10 columns:\n")

for idx in range(min(50, len(df))):
    row = df.iloc[idx, :10]
    # Show non-null values
    values = []
    for i, val in enumerate(row):
        if pd.notna(val) and str(val).strip():
            values.append(f"Col{i}={val}")
    if values:
        print(f"Row {idx:2d}: {' | '.join(values)}")
