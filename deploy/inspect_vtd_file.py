#!/usr/bin/env python3
import pandas as pd

file_path = '/opt/whovoted/data/district_reference/PLANC2333_r110_VTD24G.xls'

# Read first few rows to see structure
df = pd.read_excel(file_path, sheet_name=0, header=None, nrows=20)

print("First 20 rows of the file:")
print(df.to_string())

print("\n\nColumn count:", len(df.columns))
