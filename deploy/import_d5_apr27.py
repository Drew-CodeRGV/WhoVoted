#!/usr/bin/env python3
"""Download April 27 EV roster and import."""
import urllib.request, sqlite3, openpyxl, os

DB_PATH = '/opt/whovoted/data/whovoted.db'
URL = 'https://www.mcallen.net/docs/default-source/cityelections/2026-Special-Election/cumulative-4-27-26.xlsx?sfvrsn=0'
OUTPATH = '/opt/whovoted/data/d5_ev_4-27.xlsx'

# Download
req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
resp = urllib.request.urlopen(req, timeout=30)
with open(OUTPATH, 'wb') as f:
    f.write(resp.read())
print(f"Downloaded: {os.path.getsize(OUTPATH)/1024:.0f} KB")

# Extract VUIDs
wb = openpyxl.load_workbook(OUTPATH)
sheet = wb.active
vuids = set()
for row in sheet.iter_rows(min_row=1, values_only=True):
    for cell in row:
        if cell is None: continue
        val = str(cell).strip().replace('.0', '')
        if val.isdigit() and len(val) == 10:
            vuids.add(val)
print(f"April 27 VUIDs: {len(vuids)}")

# Import
conn = sqlite3.connect(DB_PATH)
before = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date='2026-05-02'").fetchone()[0]
for vuid in vuids:
    conn.execute("INSERT OR IGNORE INTO voter_elections (vuid, election_date, election_year, election_type, voting_method, party_voted) VALUES (?, '2026-05-02', '2026', 'special', 'early-voting', '')", (vuid,))
conn.commit()
after = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date='2026-05-02'").fetchone()[0]
print(f"DB: {before} → {after} (+{after-before} new)")
print(f"Total D5 in DB: {after} (expected: 1,145)")
conn.close()
