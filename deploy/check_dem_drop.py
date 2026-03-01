#!/usr/bin/env python3
"""Check why 3 DEM records were dropped."""
import sys
sys.path.insert(0, '/opt/whovoted/backend')

import pandas as pd
from processor import read_data_file
from vuid_resolver import normalize_column_names, has_vuid_column, VUIDResolver

csv_path = '/opt/whovoted/uploads/d6cdd20a-2eca-47df-a6be-df3c8e0be472_EV_DEM_Roster_March_3_2026_Cumulative_202602250654232301.xlsx'

df = read_data_file(csv_path)
print(f"Raw rows after read: {len(df)}")

df = normalize_column_names(df)
print(f"After normalize_column_names: {len(df)}")
print(f"Columns: {list(df.columns)}")

if 'vuid' not in df.columns:
    print("ERROR: No vuid column!")
    sys.exit(1)

print(f"\nVUID column stats:")
print(f"  Total rows: {len(df)}")
print(f"  NaN VUIDs: {df['vuid'].isna().sum()}")
print(f"  Empty string VUIDs: {(df['vuid'].astype(str).str.strip() == '').sum()}")

# Drop NaN and empty
df_clean = df.dropna(subset=['vuid'])
df_clean = df_clean[df_clean['vuid'].astype(str).str.strip() != '']
print(f"  After dropping NaN/empty: {len(df_clean)}")

# Check for duplicate VUIDs
vuids = df_clean['vuid'].astype(str).str.strip()
print(f"  Unique VUIDs: {vuids.nunique()}")
print(f"  Duplicate VUIDs: {vuids.duplicated().sum()}")

if vuids.duplicated().sum() > 0:
    dups = vuids[vuids.duplicated(keep=False)]
    print(f"  Duplicate VUID values: {dups.unique()[:10]}")

# Check normalization
normalized = vuids.apply(lambda x: str(x).strip().lstrip('0') or '0')
print(f"  Unique normalized VUIDs: {normalized.nunique()}")

# The GeoJSON deduplicates by normalized VUID
diff = len(df_clean) - normalized.nunique()
print(f"\n  Records that would be deduped in GeoJSON: {diff}")
print(f"  Expected GeoJSON features: {normalized.nunique()}")
