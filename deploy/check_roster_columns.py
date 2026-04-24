#!/usr/bin/env python3
"""Check what columns are in the roster Excel file and find unmapped voters."""
import requests, sqlite3, re, openpyxl
from io import BytesIO

ROSTER_URL = 'https://www.hidalgocounty.us/DocumentCenter/View/72488/EV-Roster-May-2-2026-Cumulative'
DB_PATH = '/opt/whovoted/data/whovoted.db'

print("Downloading roster...")
resp = requests.get(ROSTER_URL, timeout=30)
wb = openpyxl.load_workbook(BytesIO(resp.content))
sheet = wb.active

# Show headers
headers = [cell.value for cell in sheet[1]]
print(f"\nColumns ({len(headers)}):")
for i, h in enumerate(headers):
    print(f"  [{i}] {h}")

# Show first 3 data rows
print("\nSample rows:")
for row in list(sheet.iter_rows(min_row=2, max_row=4, values_only=True)):
    print(f"  {row}")

# Find VUID column
vuid_col = None
name_col = None
for i, h in enumerate(headers):
    if h and 'VUID' in str(h).upper():
        vuid_col = i
    if h and 'NAME' in str(h).upper() and 'FIRST' not in str(h).upper() and 'LAST' not in str(h).upper():
        name_col = i

# Extract all VUIDs and names
roster_data = {}
for row in sheet.iter_rows(min_row=2, values_only=True):
    vuid = str(row[vuid_col]).strip() if vuid_col is not None and row[vuid_col] else None
    if vuid and re.match(r'^\d{10}$', vuid):
        # Try to get name from various columns
        name = None
        for i, val in enumerate(row):
            h = headers[i] if i < len(headers) else ''
            if h and 'NAME' in str(h).upper():
                name = str(val).strip() if val else name
                break
        if not name:
            name = str(row[2]).strip() if len(row) > 2 and row[2] else 'Unknown'
        roster_data[vuid] = name

print(f"\nTotal VUIDs in roster: {len(roster_data)}")

# Check which are NOT in voters table
conn = sqlite3.connect(DB_PATH)
all_vuids = list(roster_data.keys())
placeholders = ','.join('?' * len(all_vuids))
existing = set(r[0] for r in conn.execute(f"SELECT vuid FROM voters WHERE vuid IN ({placeholders})", all_vuids).fetchall())

unmapped = {v: roster_data[v] for v in all_vuids if v not in existing}
print(f"Unmapped voters (not in DB): {len(unmapped)}")
for vuid, name in sorted(unmapped.items(), key=lambda x: x[1]):
    print(f"  VUID {vuid}: {name}")

conn.close()
