#!/usr/bin/env python3
"""Examine the actual data structure of the XLS files."""

import pandas as pd

# Read the file
df = pd.read_excel('data/district_reference/PLANC2333_r150.xls', skiprows=6, engine='xlrd')

print("Columns:", list(df.columns))
print(f"\nTotal rows: {len(df)}")
print("\nFirst 30 rows:")
print(df[['County', 'District']].head(30).to_string())

print("\n\nUnique districts:")
print(df['District'].unique()[:20])

print("\n\nSample rows where District is not NaN:")
sample = df[df['District'].notna()].head(20)
print(sample[['County', 'District']].to_string())
