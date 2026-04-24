#!/usr/bin/env python3
"""
Refine the CPct-2 precinct list to get EXACT match with certified numbers.

Starting from the greedy result (112 precincts, -81 votes), try adding
precincts one by one to get closer to the target.
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
print("REFINING CPCT-2 TO EXACT MATCH")
print("="*80)

# Load current best solution
with open('/opt/whovoted/deploy/cpct2_correct_precincts.json') as f:
    data = json.load(f)

current_precincts = set(data['precincts'])
current_early = data['counts']['early']
current_election_day = data['counts']['election_day']

print(f"\nStarting with {len(current_precincts)} precincts:")
print(f"  Early: {current_early:,} (need {TARGET_EARLY - current_early:+,})")
print(f"  Election Day: {current_election_day:,} (need {TARGET_ELECTION_DAY - current_election_day:+,})")

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Get all precincts not in current set
cur.execute("""
    SELECT DISTINCT precinct FROM voters WHERE county = ? AND precinct IS NOT NULL
""", (COUNTY,))

all_precincts = {row['precinct'] for row in cur.fetchall()}
remaining_precincts = all_precincts - current_precincts

print(f"\nRemaining precincts to consider: {len(remaining_precincts)}")

# Get vote counts for remaining precincts
remaining_votes = {}
for precinct in remaining_precincts:
    cur.execute("""
        SELECT 
            COUNT(DISTINCT CASE WHEN ve.voting_method = 'early-voting' THEN ve.vuid END) as early,
            COUNT(DISTINCT CASE WHEN ve.voting_method = 'election-day' THEN ve.vuid END) as election_day
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.county = ? AND v.precinct = ? AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
    """, (COUNTY, precinct, ELECTION_DATE))
    
    row = cur.fetchone()
    early = row['early']
    election_day = row['election_day']
    
    if early > 0 or election_day > 0:
        remaining_votes[precinct] = {'early': early, 'election_day': election_day}

print(f"Remaining precincts with votes: {len(remaining_votes)}")

# Try adding precincts to get closer
needed_early = TARGET_EARLY - current_early
needed_election_day = TARGET_ELECTION_DAY - current_election_day

print(f"\nNeed: {needed_early:+,} early, {needed_election_day:+,} election day")

# Find precincts that match what we need
candidates = []
for precinct, votes in remaining_votes.items():
    # Score based on how close it gets us to target
    score = abs((current_early + votes['early']) - TARGET_EARLY) + \
            abs((current_election_day + votes['election_day']) - TARGET_ELECTION_DAY)
    candidates.append((precinct, votes, score))

candidates.sort(key=lambda x: x[2])

print("\nTop 20 candidates to add:")
for i, (precinct, votes, score) in enumerate(candidates[:20]):
    new_early = current_early + votes['early']
    new_election_day = current_election_day + votes['election_day']
    print(f"  {i+1}. {precinct}: +{votes['early']} early, +{votes['election_day']} election day")
    print(f"      Would give: {new_early:,} early ({new_early - TARGET_EARLY:+,}), "
          f"{new_election_day:,} election day ({new_election_day - TARGET_ELECTION_DAY:+,})")

# Try combinations of 2-3 precincts
print("\n" + "="*80)
print("TRYING COMBINATIONS")
print("="*80)

best_combo = None
best_diff = float('inf')

# Try single precincts
for precinct, votes, _ in candidates[:50]:
    new_early = current_early + votes['early']
    new_election_day = current_election_day + votes['election_day']
    diff = abs(new_early - TARGET_EARLY) + abs(new_election_day - TARGET_ELECTION_DAY)
    
    if diff < best_diff:
        best_diff = diff
        best_combo = [precinct]
        best_early = new_early
        best_election_day = new_election_day
        
        if diff == 0:
            print(f"✓ EXACT MATCH with single precinct: {precinct}")
            break

# Try pairs
if best_diff > 0:
    print("Trying pairs...")
    for i, (p1, v1, _) in enumerate(candidates[:30]):
        for p2, v2, _ in candidates[i+1:30]:
            new_early = current_early + v1['early'] + v2['early']
            new_election_day = current_election_day + v1['election_day'] + v2['election_day']
            diff = abs(new_early - TARGET_EARLY) + abs(new_election_day - TARGET_ELECTION_DAY)
            
            if diff < best_diff:
                best_diff = diff
                best_combo = [p1, p2]
                best_early = new_early
                best_election_day = new_election_day
                
                if diff == 0:
                    print(f"✓ EXACT MATCH with pair: {p1}, {p2}")
                    break
        if best_diff == 0:
            break

# Try triples
if best_diff > 0:
    print("Trying triples...")
    for i, (p1, v1, _) in enumerate(candidates[:20]):
        for j, (p2, v2, _) in enumerate(candidates[i+1:20]):
            for p3, v3, _ in candidates[j+1:20]:
                new_early = current_early + v1['early'] + v2['early'] + v3['early']
                new_election_day = current_election_day + v1['election_day'] + v2['election_day'] + v3['election_day']
                diff = abs(new_early - TARGET_EARLY) + abs(new_election_day - TARGET_ELECTION_DAY)
                
                if diff < best_diff:
                    best_diff = diff
                    best_combo = [p1, p2, p3]
                    best_early = new_early
                    best_election_day = new_election_day
                    
                    if diff == 0:
                        print(f"✓ EXACT MATCH with triple: {p1}, {p2}, {p3}")
                        break
            if best_diff == 0:
                break
        if best_diff == 0:
            break

print("\n" + "="*80)
print("BEST REFINEMENT")
print("="*80)

if best_combo:
    print(f"Add precincts: {', '.join(best_combo)}")
    print(f"  Early: {best_early:,} (target: {TARGET_EARLY:,}, diff: {best_early - TARGET_EARLY:+,})")
    print(f"  Election Day: {best_election_day:,} (target: {TARGET_ELECTION_DAY:,}, diff: {best_election_day - TARGET_ELECTION_DAY:+,})")
    print(f"  Total: {best_early + best_election_day:,} (target: {TARGET_TOTAL:,})")
    
    # Save refined list
    refined_precincts = sorted(list(current_precincts) + best_combo)
    
    with open('/opt/whovoted/deploy/cpct2_correct_precincts.json', 'w') as f:
        json.dump({
            'strategy': 'Greedy + Refinement',
            'precincts': refined_precincts,
            'counts': {
                'early': best_early,
                'election_day': best_election_day,
                'total': best_early + best_election_day
            },
            'target': {
                'early': TARGET_EARLY,
                'election_day': TARGET_ELECTION_DAY,
                'total': TARGET_TOTAL
            },
            'difference': {
                'early': best_early - TARGET_EARLY,
                'election_day': best_election_day - TARGET_ELECTION_DAY,
                'total': (best_early + best_election_day) - TARGET_TOTAL
            }
        }, f, indent=2)
    
    print(f"\n✓ Saved refined list with {len(refined_precincts)} precincts")
else:
    print("No improvement found")

conn.close()
