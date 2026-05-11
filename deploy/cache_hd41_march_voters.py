#!/usr/bin/env python3
"""Cache individual voter-level data for HD-41 March primary (for dot map + popups)."""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_voters.json'
ELECTION_DATE = '2026-03-03'

def main():
    print("Caching HD-41 March primary voter data (individual dots)...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    voters_raw = conn.execute("""
        SELECT v.vuid, v.lat, v.lng, v.precinct, v.address, v.city, v.zip,
               v.firstname, v.lastname, v.birth_year, v.sex, v.current_party,
               ve.party_voted, ve.voting_method
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ? AND v.state_house_district = 'HD-41'
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
        ORDER BY v.precinct
    """, (ELECTION_DATE,)).fetchall()

    voters = []
    vuids = []
    for row in voters_raw:
        vuids.append(row['vuid'])
        voters.append({
            'vuid': row['vuid'],
            'lat': row['lat'], 'lng': row['lng'],
            'precinct': row['precinct'],
            'address': row['address'], 'city': row['city'], 'zip': row['zip'],
            'name': f"{row['firstname'] or ''} {row['lastname'] or ''}".strip(),
            'birth_year': row['birth_year'], 'sex': row['sex'],
            'party_voted': row['party_voted'],
            'voting_method': row['voting_method'],
            'hist': [],
        })

    # Voting history
    if vuids:
        vuid_to_idx = {v['vuid']: i for i, v in enumerate(voters)}
        # Batch in chunks to avoid SQL variable limit
        chunk_size = 500
        for start in range(0, len(vuids), chunk_size):
            chunk = vuids[start:start+chunk_size]
            ph = ','.join('?' * len(chunk))
            hist_rows = conn.execute(f"""
                SELECT vuid, election_date, party_voted
                FROM voter_elections
                WHERE vuid IN ({ph}) AND election_date != ?
                ORDER BY election_date
            """, chunk + [ELECTION_DATE]).fetchall()
            for hr in hist_rows:
                idx = vuid_to_idx.get(hr['vuid'])
                if idx is not None and hr['party_voted']:
                    p = hr['party_voted']
                    letter = 'D' if 'democrat' in p.lower() else 'R' if 'republican' in p.lower() else 'O'
                    ed = hr['election_date'] or ''
                    voters[idx]['hist'].append({'y': ed[:4], 'p': letter})

    conn.close()

    # Method breakdown
    methods = {}
    for v in voters:
        m = v.get('voting_method') or 'unknown'
        methods[m] = methods.get(m, 0) + 1

    data = {
        'voters': voters,
        'count': len(voters),
        'method_breakdown': methods,
        'election_date': ELECTION_DATE,
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    print(f"✓ Cached {len(voters)} voters ({Path(CACHE_PATH).stat().st_size/1024/1024:.1f} MB)")
    print(f"  Methods: {methods}")

if __name__ == '__main__':
    main()
