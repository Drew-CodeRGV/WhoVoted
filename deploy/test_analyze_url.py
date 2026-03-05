#!/usr/bin/env python3
"""
Test the analyze_url function directly to see what it returns
"""
import sys
sys.path.insert(0, '/opt/whovoted/backend')

# Simulate the analyze_url logic
from urllib.parse import urlparse, unquote

url = "https://www.hidalgocounty.us/DocumentCenter/View/72236/ED%20REP%20Roster%20March%203%2C%202026%20%28Cumulative%29.xlsx"

# Get filename from URL
path = urlparse(url).path
filename = unquote(path.split('/')[-1]) if path else ''

print(f"URL: {url}")
print(f"Filename (decoded): {filename}")
print()

# Create combined string
fn_lower = filename.lower()
url_lower = url.lower()
combined = fn_lower + ' ' + url_lower

print(f"fn_lower: {fn_lower}")
print(f"url_lower: {url_lower}")
print(f"combined: {combined[:200]}...")
print()

# Test year detection
import re
year = ''
year_match = re.search(r'20[12]\d', fn_lower)
if year_match:
    year = year_match.group()
    print(f"Year found in fn_lower: {year}")
else:
    year_match = re.search(r'20[12]\d', url_lower)
    if year_match:
        year = year_match.group()
        print(f"Year found in url_lower: {year}")

# Test voting method detection
voting_method = ''
if any(x in combined for x in ['abbm', 'mail-in', 'mail_in', 'mailin', 'mail ballot', 'absentee']):
    voting_method = 'mail-in'
elif any(x in combined for x in ['early vot', 'early_vot', 'earlyvot', ' ev ', '_ev_', '-ev-', 'ev roster', 'ev_roster']):
    voting_method = 'early-voting'
elif any(x in combined for x in ['election day', 'election_day', 'electionday', ' ed ', '_ed_', '-ed-', 'eday', 'ed roster', 'ed_roster']) or combined.startswith('ed ') or combined.startswith('ed%20'):
    voting_method = 'election-day'

print(f"Voting method: {voting_method}")
print()

# Test month detection
month_names = {
    'january': '01', 'february': '02', 'march': '03', 'april': '04',
    'may': '05', 'june': '06', 'july': '07', 'august': '08',
    'september': '09', 'october': '10', 'november': '11', 'december': '12',
}

election_date = ''
for mname, mnum in month_names.items():
    m = re.search(mname + r'\s+(\d{1,2})\s*,?\s*(20\d{2})', combined)
    if m:
        day = int(m.group(1))
        yr = m.group(2)
        election_date = f"{yr}-{mnum}-{day:02d}"
        print(f"Election date found: {election_date}")
        if not year:
            year = yr
            print(f"Year updated from date: {year}")
        break

print()
print("RESULTS:")
print(f"  Year: {year}")
print(f"  Voting Method: {voting_method}")
print(f"  Election Date: {election_date}")
