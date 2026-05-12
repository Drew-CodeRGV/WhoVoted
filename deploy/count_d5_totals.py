#!/usr/bin/env python3
"""Count D5 election totals from all sources."""
import openpyxl, os

DATA_DIR = '/opt/whovoted/data'

# Early voting cumulative (April 28 = final)
ev_path = os.path.join(DATA_DIR, 'd5_ev_cumulative_final.xlsx')
# Mail ballots
mail_path = os.path.join(DATA_DIR, 'd5_mail_ballots.xlsx')
# Election day
eday_path = os.path.join(DATA_DIR, 'd5_election_day.xlsx')

def count_vuids(filepath):
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

ev_vuids = count_vuids(ev_path) if os.path.exists(ev_path) else set()
mail_vuids = count_vuids(mail_path) if os.path.exists(mail_path) else set()
eday_vuids = count_vuids(eday_path) if os.path.exists(eday_path) else set()

# Check overlaps
all_vuids = ev_vuids | mail_vuids | eday_vuids
ev_and_mail = ev_vuids & mail_vuids
ev_and_eday = ev_vuids & eday_vuids
mail_and_eday = mail_vuids & eday_vuids

print("=== McAllen City Commission D5 (May 2, 2026) ===")
print(f"\nFrom files:")
print(f"  Early Voting (cumulative Apr 28): {len(ev_vuids)} unique VUIDs")
print(f"  Mail-In Ballots:                  {len(mail_vuids)} unique VUIDs")
print(f"  Election Day (McHi):              {len(eday_vuids)} unique VUIDs")
print(f"  ─────────────────────────────────────────")
print(f"  Total unique VUIDs:               {len(all_vuids)}")
print(f"\nOverlaps (should be 0 if data is clean):")
print(f"  EV ∩ Mail:      {len(ev_and_mail)}")
print(f"  EV ∩ E-Day:     {len(ev_and_eday)}")
print(f"  Mail ∩ E-Day:   {len(mail_and_eday)}")
print(f"\nExpected total (from official results): 1,145")
print(f"We have:                                 {len(all_vuids)}")
print(f"Missing:                                 {1145 - len(all_vuids)}")

# Check DB
import sqlite3
conn = sqlite3.connect('/opt/whovoted/data/whovoted.db')
db_count = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections WHERE election_date='2026-05-02'").fetchone()[0]
print(f"\nIn database (voter_elections):           {db_count}")
conn.close()
