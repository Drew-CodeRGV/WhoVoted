#!/usr/bin/env python3
"""Test script to examine XLS file structure."""

import pandas as pd

# Try reading with different skiprows values
for skip in [0, 3, 4, 5, 6]:
    print(f'\n=== SKIPROWS={skip} ===')
    try:
        df = pd.read_excel('data/district_reference/PLANC2333_r150.xls', skiprows=skip, engine='xlrd')
        print(f'Columns: {list(df.columns)[:5]}')
        print(f'First row: {df.iloc[0].tolist()[:5]}')
        if 'County' in df.columns or 'District' in df.columns:
            print('FOUND IT!')
            print(f'All columns: {list(df.columns)}')
            print(f'\nFirst 5 data rows:')
            print(df.head())
            break
    except Exception as e:
        print(f'Error: {e}')
