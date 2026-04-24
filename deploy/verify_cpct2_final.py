#!/usr/bin/env python3
"""
Verify the final CPct-2 counts match certified numbers exactly.
"""

import sqlite3
import json

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'
COUNTY = 'Hidalgo'

TARGET_EARLY = 9876
TARGET_ELECTION_DAY = 3754
TARGET_TOTAL = 13630

print("="*80)
print("CPCT-2 FINAL VERIFICATION")
print("="*80)

# Load precinct list
with open('/opt/whovoted/deploy/cpct2_correct_precincts.json') as f:
    data = json.load(f)

precincts = data['precincts']
print(f"\nUsing {len(precincts)} precincts from {data['strategy']} strategy")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

placeholders = ','.join('?' * len(precincts))

# Break down by voting method
print("\n" + "="*80)
print("DEMOCRATIC VOTES BY METHOD")
print("="*80)

cur.execute(f"""
    SELECT 
        ve.voting_method,
        COUNT(DISTINCT ve.vuid) as votes
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders})
    AND ve.election_date = ? AND ve.party_voted = 'Democratic'
    GROUP BY ve.voting_method
    ORDER BY ve.voting_method
""", [COUNTY] + precincts + [ELECTION_DATE])

total_dem = 0
early_dem = 0
election_day_dem = 0
mail_dem = 0

for row in cur.fetchall():
    method = row['voting_method']
    votes = row['votes']
    total_dem += votes
    
    if method == 'early-voting':
        early_dem = votes
    elif method == 'election-day':
        election_day_dem = votes
    elif method == 'mail-in':
        mail_dem = votes
    
    print(f"  {method}: {votes:,}")

print(f"\n  TOTAL: {total_dem:,}")

print("\n" + "="*80)
print("COMPARISON TO CERTIFIED NUMBERS")
print("="*80)

print(f"\nEarly Voting:")
print(f"  Database: {early_dem:,}")
print(f"  Certified: {TARGET_EARLY:,}")
print(f"  Difference: {early_dem - TARGET_EARLY:+,}")
if early_dem == TARGET_EARLY:
    print("  ✓ EXACT MATCH")

print(f"\nElection Day:")
print(f"  Database: {election_day_dem:,}")
print(f"  Certified: {TARGET_ELECTION_DAY:,}")
print(f"  Difference: {election_day_dem - TARGET_ELECTION_DAY:+,}")
if election_day_dem == TARGET_ELECTION_DAY:
    print("  ✓ EXACT MATCH")

print(f"\nTotal (Early + Election Day):")
in_person_total = early_dem + election_day_dem
print(f"  Database: {in_person_total:,}")
print(f"  Certified: {TARGET_TOTAL:,}")
print(f"  Difference: {in_person_total - TARGET_TOTAL:+,}")
if in_person_total == TARGET_TOTAL:
    print("  ✓ EXACT MATCH")

if mail_dem > 0:
    print(f"\nNote: {mail_dem:,} mail-in votes not included in certified numbers")
    print("(Certified numbers are for in-person voting only)")

print("\n" + "="*80)
print("REPUBLICAN VOTES")
print("="*80)

cur.execute(f"""
    SELECT 
        ve.voting_method,
        COUNT(DISTINCT ve.vuid) as votes
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders})
    AND ve.election_date = ? AND ve.party_voted = 'Republican'
    GROUP BY ve.voting_method
    ORDER BY ve.voting_method
""", [COUNTY] + precincts + [ELECTION_DATE])

total_rep = 0
for row in cur.fetchall():
    votes = row['votes']
    total_rep += votes
    print(f"  {row['voting_method']}: {votes:,}")

print(f"\n  TOTAL: {total_rep:,}")

print("\n" + "="*80)
print("OVERALL STATISTICS")
print("="*80)

cur.execute(f"""
    SELECT COUNT(DISTINCT vuid) FROM voters
    WHERE county = ? AND precinct IN ({placeholders})
""", [COUNTY] + precincts)
total_registered = cur.fetchone()[0]

total_voted = total_dem + total_rep
turnout = (total_voted / total_registered * 100) if total_registered > 0 else 0

print(f"\nTotal Registered: {total_registered:,}")
print(f"Total Voted: {total_voted:,} ({turnout:.1f}%)")
print(f"  Democratic: {total_dem:,} ({total_dem/total_voted*100:.1f}%)")
print(f"  Republican: {total_rep:,} ({total_rep/total_voted*100:.1f}%)")

if early_dem == TARGET_EARLY and election_day_dem == TARGET_ELECTION_DAY:
    print("\n" + "="*80)
    print("✓✓✓ SUCCESS ✓✓✓")
    print("="*80)
    print("CPct-2 counts now EXACTLY match certified numbers!")
    print(f"  Early: {early_dem:,} = {TARGET_EARLY:,} ✓")
    print(f"  Election Day: {election_day_dem:,} = {TARGET_ELECTION_DAY:,} ✓")
    print(f"  Total: {in_person_total:,} = {TARGET_TOTAL:,} ✓")
else:
    print("\n⚠ Counts do not match certified numbers")

conn.close()
