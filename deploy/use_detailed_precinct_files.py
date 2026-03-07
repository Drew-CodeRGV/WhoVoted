#!/usr/bin/env python3
"""
Use the detailed precinct files (r370/r380) which should have more complete data
"""
import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = Path('/opt/whovoted/data/district_reference')

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def parse_precinct_file(file_path):
    """Parse r370/r380 precinct files"""
    log(f"Parsing {file_path.name}...")
    
    df = pd.read_excel(file_path, sheet_name=0, header=None)
    
    log(f"  File shape: {df.shape}")
    log(f"  First few rows:")
    for idx in range(min(10, len(df))):
        row_data = []
        for col_idx in range(min(10, len(df.columns))):
            val = df.iloc[idx, col_idx]
            if pd.notna(val) and str(val).strip():
                row_data.append(f"Col{col_idx}={val}")
        if row_data:
            log(f"    Row {idx}: {' | '.join(row_data)}")
    
    return {}

# Check what files we have
log("="*80)
log("CHECKING DETAILED PRECINCT FILES")
log("="*80)

files = [
    'PLANC2333_r370_Prec24G.xls',
    'PLANC2333_r380_Prec24G.xls',
    'PLANS2168_r370_Prec2024 General.xls',
    'PLANS2168_r380_Prec2024 General.xls',
    'PLANH2316_r370_Prec2024 General.xls',
    'PLANH2316_r380_Prec2024 General.xls',
]

for filename in files:
    file_path = DATA_DIR / filename
    if file_path.exists():
        size_mb = file_path.stat().st_size / (1024 * 1024)
        log(f"\n✓ {filename} ({size_mb:.1f}MB)")
        if size_mb > 0.01:  # Only parse if file has content
            parse_precinct_file(file_path)
    else:
        log(f"\n✗ {filename} NOT FOUND")
