#!/usr/bin/env python3
"""Pre-cache HD-41 voter data for fast loading."""

import sys
import json
import sqlite3
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_voters.json'
# HD-41 runoff election — May 26, 2026
# Both parties headed to runoff: Dem (Salinas vs Haddad), Rep (Sanchez vs Groves)
ELECTION_DATE = '2026-05-26'
DISTRICT = 'HD-41'

def main():
    print(f"Caching {DISTRICT} voter data...")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Get all voters in HD-41 who voted in the election
    voter_rows = conn.execute("""
        SELECT
            v.vuid, v.lat, v.lng, v.precinct, v.address, v.city, v.zip,
            v.firstname, v.lastname, v.birth_year, v.sex, v.current_party,
            ve.party_voted, ve.voting_method
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ?
        AND v.state_house_district = ?
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
        ORDER BY v.precinct, v.address
    """, (ELECTION_DATE, DISTRICT)).fetchall()

    voters = []
    vuids = []
    for row in voter_rows:
        vuids.append(row['vuid'])
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
            'voting_method': row['voting_method'],
            'hist': [],
        })

    # Build voting history for each voter
    if vuids:
        vuid_to_idx = {v['vuid']: i for i, v in enumerate(voters)}
        placeholders = ','.join('?' * len(vuids))
        hist_rows = conn.execute(f"""
            SELECT vuid, election_date, party_voted
            FROM voter_elections
            WHERE vuid IN ({placeholders}) AND election_date != ?
            ORDER BY election_date
        """, vuids + [ELECTION_DATE]).fetchall()
        for hr in hist_rows:
            idx = vuid_to_idx.get(hr['vuid'])
            if idx is not None and hr['party_voted']:
                p = hr['party_voted']
                pl = p.lower()
                if 'democrat' in pl or pl == 'd':
                    letter = 'D'
                elif 'republican' in pl or pl == 'r':
                    letter = 'R'
                else:
                    letter = 'O'
                ed = hr['election_date'] or ''
                yr = ed[:4] if len(ed) >= 4 else ''
                mo = ed[5:7] if len(ed) >= 7 else ''
                voters[idx]['hist'].append({'y': yr, 'p': letter, 't': mo})

    # Voting method breakdown
    method_counts = {}
    for v in voters:
        m = v.get('voting_method', 'unknown') or 'unknown'
        method_counts[m] = method_counts.get(m, 0) + 1

    # Last data added
    last_added_row = conn.execute("""
        SELECT MAX(ve.created_at) as last_added
        FROM voter_elections ve
        INNER JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ? AND v.state_house_district = ?
    """, (ELECTION_DATE, DISTRICT)).fetchone()
    last_data_added = last_added_row['last_added'] if last_added_row else None

    # Import log
    import_log_rows = conn.execute("""
        SELECT DATE(ve.created_at) as import_date,
               MAX(ve.created_at) as last_at,
               COUNT(DISTINCT ve.vuid) as records
        FROM voter_elections ve
        INNER JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ? AND v.state_house_district = ?
        GROUP BY DATE(ve.created_at)
        ORDER BY import_date DESC
    """, (ELECTION_DATE, DISTRICT)).fetchall()
    import_log = [{'date': r['import_date'], 'time': r['last_at'], 'records': r['records']} for r in import_log_rows]

    # Unmapped voters (voted but no geocoded address)
    unmapped_rows = conn.execute("""
        SELECT v.vuid, v.firstname, v.lastname, v.precinct
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ?
        AND v.state_house_district = ?
        AND (v.geocoded = 0 OR v.lat IS NULL)
        ORDER BY v.lastname, v.firstname
    """, (ELECTION_DATE, DISTRICT)).fetchall()
    unmapped_voters = [{'vuid': r['vuid'], 'name': f"{r['firstname'] or ''} {r['lastname'] or ''}".strip(),
                        'precinct': r['precinct']} for r in unmapped_rows]

    conn.close()

    # Write cache
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    data = {
        'voters': voters,
        'unmapped_voters': unmapped_voters,
        'count': len(voters),
        'unmapped_count': len(unmapped_voters),
        'total_voted': len(voters) + len(unmapped_voters),
        'method_breakdown': method_counts,
        'last_data_added': last_data_added,
        'import_log': import_log
    }
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    print(f"✓ Cached {len(voters)} voters to {CACHE_PATH}")
    print(f"  Unmapped: {len(unmapped_voters)}")
    print(f"  File size: {Path(CACHE_PATH).stat().st_size / 1024:.1f} KB")

if __name__ == '__main__':
    main()
