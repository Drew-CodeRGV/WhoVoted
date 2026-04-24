#!/usr/bin/env python3
"""Pre-cache McAllen ISD Bond 2026 voter data for fast loading."""

import sys
import json
import sqlite3
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_voters.json'
ELECTION_DATE = '2026-05-10'

def main():
    print("Caching McAllen ISD Bond 2026 voter data...")
    
    # McAllen zip codes
    MCALLEN_ZIPS = ('78501', '78502', '78503', '78504', '78505')
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get all voters with full details, filtered by McAllen zip codes
    voter_rows = conn.execute("""
        SELECT 
            v.vuid,
            v.lat,
            v.lng,
            v.precinct,
            v.address,
            v.city,
            v.zip,
            v.firstname,
            v.lastname,
            v.birth_year,
            v.sex,
            v.current_party,
            ve.party_voted,
            ve.voting_method
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ?
        AND v.lat IS NOT NULL
        AND v.lng IS NOT NULL
        AND v.zip IN (?, ?, ?, ?, ?)
        ORDER BY v.precinct, v.address
    """, (ELECTION_DATE,) + MCALLEN_ZIPS).fetchall()
    
    voters = []
    for row in voter_rows:
        voters.append({
            'vuid': row['vuid'],
            'lat': row['lat'],
            'lng': row['lng'],
            'precinct': row['precinct'],
            'address': row['address'],
            'city': row['city'],
            'zip': row['zip'],
            'firstname': row['firstname'],
            'lastname': row['lastname'],
            'name': f"{row['firstname'] or ''} {row['lastname'] or ''}".strip(),
            'birth_year': row['birth_year'],
            'sex': row['sex'],
            'current_party': row['current_party'],
            'party_voted': row['party_voted'],
            'voting_method': row['voting_method']
        })
    
    conn.close()
    
    # Also fetch unmapped voters from the roster (voters in roster but not in DB)
    unmapped = []
    try:
        import requests, openpyxl, re
        from io import BytesIO
        ROSTER_URL = 'https://www.hidalgocounty.us/DocumentCenter/View/72488/EV-Roster-May-2-2026-Cumulative'
        resp = requests.get(ROSTER_URL, timeout=30)
        wb = openpyxl.load_workbook(BytesIO(resp.content))
        sheet = wb.active
        headers = [cell.value for cell in sheet[1]]
        
        # Find column indices
        vuid_col = next((i for i, h in enumerate(headers) if h and 'VUID' in str(h).upper()), None)
        name_col = next((i for i, h in enumerate(headers) if h and 'NAME' in str(h).upper()), 0)
        pct_col = next((i for i, h in enumerate(headers) if h and 'PRECINCT' in str(h).upper()), None)
        
        mapped_vuids = {v['vuid'] for v in voters}
        conn2 = sqlite3.connect(DB_PATH)
        all_db_vuids = set(r[0] for r in conn2.execute("SELECT vuid FROM voters").fetchall())
        conn2.close()
        
        for row in sheet.iter_rows(min_row=2, values_only=True):
            vuid = str(row[vuid_col]).strip() if vuid_col is not None and row[vuid_col] else None
            if not vuid or not re.match(r'^\d{10}$', vuid):
                continue
            if vuid in mapped_vuids or vuid in all_db_vuids:
                continue
            raw_name = str(row[name_col]).strip() if row[name_col] else 'Unknown'
            pct = str(row[pct_col]).strip() if pct_col is not None and row[pct_col] else None
            # Parse "LAST, FIRST MIDDLE" format
            parts = raw_name.split(',', 1)
            lastname = parts[0].strip()
            firstname = parts[1].strip() if len(parts) > 1 else ''
            unmapped.append({
                'vuid': vuid,
                'name': f"{firstname} {lastname}".strip(),
                'precinct': pct,
                'unmapped': True
            })
        print(f"  Unmapped voters from roster: {len(unmapped)}")
    except Exception as e:
        print(f"  Warning: Could not fetch unmapped voters: {e}")
    
    # Compute voting method breakdown
    method_counts = {}
    for v in voters:
        m = v.get('voting_method', 'unknown') or 'unknown'
        method_counts[m] = method_counts.get(m, 0) + 1
    
    # Write to cache file
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    data = {
        'voters': voters,
        'unmapped': unmapped,
        'count': len(voters),
        'unmapped_count': len(unmapped),
        'total_voted': len(voters) + len(unmapped),
        'method_breakdown': method_counts
    }
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    
    print(f"✓ Cached {len(voters)} voters (McAllen zip codes only) to {CACHE_PATH}")
    print(f"  File size: {Path(CACHE_PATH).stat().st_size / 1024:.1f} KB")

if __name__ == '__main__':
    main()
