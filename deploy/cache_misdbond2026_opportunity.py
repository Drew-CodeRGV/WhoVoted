#!/usr/bin/env python3
"""Cache household-level voter opportunity data for McAllen ISD Bond 2026.

Classifies each registered McAllen voter who HASN'T voted in the bond into:
- "regular": Voted in 3+ past elections (high-propensity, just missed this one)
- "occasional": Voted in 1-2 past elections  
- "never": Zero voting history (registered but never voted)

Groups by household (same lat/lng) for map display.
"""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_opportunity.json'
ELECTION_DATE = '2026-05-10'
MCALLEN_ZIPS = ('78501','78502','78503','78504','78505')

def classify(election_count):
    if election_count >= 3: return 'regular'
    if election_count >= 1: return 'occasional'
    return 'never'

def main():
    print("Building household-level opportunity data...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ph = ','.join('?' * len(MCALLEN_ZIPS))
    
    # Get all McAllen voters who have NOT voted in the bond, with their history count
    rows = conn.execute(f"""
        SELECT v.vuid, v.lat, v.lng, v.address, v.firstname, v.lastname,
               v.current_party, v.birth_year, v.sex,
               (SELECT COUNT(*) FROM voter_elections ve2 
                WHERE ve2.vuid = v.vuid AND ve2.election_date != ?) as past_elections
        FROM voters v
        WHERE v.zip IN ({ph})
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
        AND v.vuid NOT IN (
            SELECT ve.vuid FROM voter_elections ve WHERE ve.election_date = ?
        )
    """, (ELECTION_DATE,) + MCALLEN_ZIPS + (ELECTION_DATE,)).fetchall()
    conn.close()
    
    print(f"Found {len(rows)} non-voters in McAllen")
    
    # Group by household (same lat/lng rounded to 6 decimals)
    households = {}
    counts = {'regular': 0, 'occasional': 0, 'never': 0}
    
    for r in rows:
        key = f"{round(r['lat'], 5)},{round(r['lng'], 5)}"
        cat = classify(r['past_elections'])
        counts[cat] += 1
        
        if key not in households:
            households[key] = {
                'lat': r['lat'], 'lng': r['lng'],
                'address': r['address'],
                'voters': []
            }
        households[key]['voters'].append({
            'name': f"{r['firstname'] or ''} {r['lastname'] or ''}".strip(),
            'party': r['current_party'] or '',
            'cat': cat,
            'past': r['past_elections']
        })
    
    # Determine household category (best voter in household)
    priority = {'regular': 3, 'occasional': 2, 'never': 1}
    hh_list = []
    for key, hh in households.items():
        best_cat = max(hh['voters'], key=lambda v: priority[v['cat']])['cat']
        # Keep compact — only include voter details for small households
        voters_compact = []
        for v in hh['voters'][:5]:  # Max 5 per household
            voters_compact.append({
                'n': v['name'],
                'c': v['cat'][0],  # r/o/n
                'p': v['past']
            })
        hh_list.append({
            'la': hh['lat'],
            'ln': hh['lng'],
            'a': hh['address'],
            't': best_cat[0],  # r/o/n
            'v': len(hh['voters']),
            'd': voters_compact
        })
    
    data = {
        'households': hh_list,
        'summary': counts,
        'total': len(rows)
    }
    
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    
    print(f"Households: {len(hh_list)}")
    print(f"Regular voters (3+ elections): {counts['regular']}")
    print(f"Occasional voters (1-2): {counts['occasional']}")
    print(f"Never voted: {counts['never']}")
    print(f"Cache: {Path(CACHE_PATH).stat().st_size / 1024 / 1024:.1f} MB")

if __name__ == '__main__':
    main()
