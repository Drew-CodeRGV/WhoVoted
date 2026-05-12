#!/usr/bin/env python3
"""
Download ALL daily EV rosters for D5 and combine.
Each file has that day's voters (not cumulative despite the name).
Expected: 827 early voters total.
"""
import urllib.request, sqlite3, json, os
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = '/opt/whovoted/data'
ELECTION_DATE = '2026-05-02'

EV_URLS = [
    ('4-20', 'https://www.mcallen.net/docs/default-source/cityelections/2026-Special-Election/cummulative-4-20-26.xlsx?sfvrsn=0'),
    ('4-21', 'https://www.mcallen.net/docs/default-source/cityelections/2026-Special-Election/cumulative-4-21-26.xlsx?sfvrsn=0'),
    ('4-22', 'https://www.mcallen.net/docs/default-source/cityelections/2026-Special-Election/cumulative-4-22-26.xlsx?sfvrsn=0'),
    ('4-23', 'https://www.mcallen.net/docs/default-source/default-document-library/cumulative-4-23-26.xlsx?sfvrsn=0'),
    ('4-24', 'https://www.mcallen.net/docs/default-source/cityelections/2026-Special-Election/cumulative-4-24-26.xlsx?sfvrsn=0'),
    ('4-25', 'https://www.mcallen.net/docs/default-source/cityelections/2026-Special-Election/cumulative-4-25-26.xlsx?sfvrsn=2'),
    ('4-28', 'https://www.mcallen.net/docs/default-source/cityelections/2026-Special-Election/cumulative-4-28-26.xlsx?sfvrsn=0'),
]

def extract_vuids(filepath):
    import openpyxl
    wb = openpyxl.load_workbook(filepath)
    sheet = wb.active
    vuids = set()
    for row in sheet.iter_rows(min_row=1, values_only=True):
        for cell in row:
            if cell is None: continue
            val = str(cell).strip().replace('.0', '')
            if val.isdigit() and len(val) == 10:
                vuids.add(val)
    return vuids

def main():
    print("Downloading ALL D5 early voting rosters...\n")
    
    all_ev_vuids = set()
    for label, url in EV_URLS:
        outpath = os.path.join(DATA_DIR, f'd5_ev_{label}.xlsx')
        print(f"  {label}: ", end='')
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            resp = urllib.request.urlopen(req, timeout=30)
            data = resp.read()
            if data[:5] == b'<html' or data[:15].startswith(b'<!DOC'):
                print("✗ (HTML error page)")
                continue
            with open(outpath, 'wb') as f:
                f.write(data)
            vuids = extract_vuids(outpath)
            new = vuids - all_ev_vuids
            all_ev_vuids.update(vuids)
            print(f"✓ {len(vuids)} VUIDs ({len(new)} new, running total: {len(all_ev_vuids)})")
        except Exception as e:
            print(f"✗ ({e})")
    
    # Mail ballots
    mail_path = os.path.join(DATA_DIR, 'd5_mail_ballots.xlsx')
    mail_vuids = extract_vuids(mail_path) if os.path.exists(mail_path) else set()
    
    # Election day
    eday_path = os.path.join(DATA_DIR, 'd5_election_day.xlsx')
    eday_vuids = extract_vuids(eday_path) if os.path.exists(eday_path) else set()
    
    total = all_ev_vuids | mail_vuids | eday_vuids
    
    print(f"\n{'='*50}")
    print(f"  Early Voting:  {len(all_ev_vuids)} (expected: 827)")
    print(f"  Mail Ballots:  {len(mail_vuids)} (expected: 70)")
    print(f"  Election Day:  {len(eday_vuids)} (expected: 246)")
    print(f"  ─────────────────────────────────")
    print(f"  TOTAL:         {len(total)} (expected: 1,145)")
    print(f"{'='*50}")
    
    # Import all into DB
    print(f"\nImporting into database...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"DELETE FROM voter_elections WHERE election_date='{ELECTION_DATE}'")
    
    for vuid in all_ev_vuids:
        conn.execute("INSERT OR IGNORE INTO voter_elections (vuid, election_date, election_year, election_type, voting_method, party_voted) VALUES (?, ?, '2026', 'special', 'early-voting', '')", (vuid, ELECTION_DATE))
    for vuid in mail_vuids:
        conn.execute("INSERT OR IGNORE INTO voter_elections (vuid, election_date, election_year, election_type, voting_method, party_voted) VALUES (?, ?, '2026', 'special', 'mail-in', '')", (vuid, ELECTION_DATE))
    for vuid in eday_vuids:
        conn.execute("INSERT OR IGNORE INTO voter_elections (vuid, election_date, election_year, election_type, voting_method, party_voted) VALUES (?, ?, '2026', 'special', 'election-day', '')", (vuid, ELECTION_DATE))
    
    conn.commit()
    final = conn.execute(f"SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date='{ELECTION_DATE}'").fetchone()[0]
    print(f"  In DB: {final}")
    conn.close()

if __name__ == '__main__':
    main()
