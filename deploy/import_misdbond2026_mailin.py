#!/usr/bin/env python3
"""Import McAllen ISD Bond 2026 mail-in ballot roster."""
import requests, sqlite3, re, sys
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-05-10'
ROSTER_URL = 'https://www.hidalgocounty.us/DocumentCenter/View/72496/ABBM-LIST-May-2-2026-Cumulative'

def main():
    print("=" * 60)
    print("McAllen ISD Bond 2026 - Mail-In Ballot Import")
    print("=" * 60)
    
    print("Downloading mail-in roster...")
    resp = requests.get(ROSTER_URL, timeout=30)
    resp.raise_for_status()
    
    # Parse Excel
    import openpyxl
    from io import BytesIO
    wb = openpyxl.load_workbook(BytesIO(resp.content))
    sheet = wb.active
    headers = [cell.value for cell in sheet[1]]
    print(f"Columns: {headers}")
    
    # Find VUID column
    vuid_col = None
    name_col = 0
    for i, h in enumerate(headers):
        if h and 'VUID' in str(h).upper():
            vuid_col = i
        if h and 'NAME' in str(h).upper():
            name_col = i
    
    vuids = set()
    names = {}
    for row in sheet.iter_rows(min_row=2, values_only=True):
        vuid = str(row[vuid_col]).strip() if vuid_col is not None and row[vuid_col] else None
        if vuid and re.match(r'^\d{10}$', vuid):
            vuids.add(vuid)
            if row[name_col]:
                names[vuid] = str(row[name_col]).strip()
    
    print(f"Extracted {len(vuids)} mail-in VUIDs")
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    # Check which exist in DB
    all_vuids = list(vuids)
    ph = ','.join('?' * len(all_vuids))
    existing = set(r[0] for r in cur.execute(f"SELECT vuid FROM voters WHERE vuid IN ({ph})", all_vuids).fetchall())
    print(f"Found {len(existing)} in voter database")
    
    imported = 0
    skipped = 0
    for vuid in all_vuids:
        if vuid not in existing:
            continue
        # Check if already imported
        row = cur.execute("SELECT voting_method FROM voter_elections WHERE vuid = ? AND election_date = ?", (vuid, ELECTION_DATE)).fetchone()
        if row:
            # Already exists - update to mail-in if it was early-voting
            if row[0] != 'mail-in':
                skipped += 1
            continue
        
        cur.execute("""
            INSERT INTO voter_elections (vuid, election_date, voting_method, data_source, created_at)
            VALUES (?, ?, 'mail-in', 'hidalgo-mailin-roster', datetime('now'))
        """, (vuid, ELECTION_DATE))
        imported += 1
    
    conn.commit()
    
    # Count not in DB
    not_in_db = len(vuids) - len(existing)
    
    print(f"\nImported: {imported} mail-in voters")
    print(f"Already in DB (early voting): {skipped}")
    print(f"Not in voter database: {not_in_db}")
    
    conn.close()
    
    # Regenerate cache
    if imported > 0:
        print("\nRegenerating cache...")
        import subprocess
        subprocess.run([sys.executable, '/opt/whovoted/deploy/cache_misdbond2026_voters.py'], check=True)
        print("Cache regenerated")
    
    print(f"\nTotal mail-in ballots: {len(vuids)}")
    return 0

if __name__ == '__main__':
    sys.exit(main())
