#!/usr/bin/env python3
"""Download and import D5 election day roster, then rebuild the D5 layer."""
import urllib.request, sqlite3, json, os
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = '/opt/whovoted/data'
DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_d5_voters.json'
EDAY_URL = 'https://www.mcallen.net/docs/default-source/cityelections/2026-Special-Election/mchi-5-2-26.xlsx?sfvrsn=0'
ELECTION_DATE = '2026-05-02'

def point_in_polygon(x, y, ring):
    n = len(ring); inside = False; j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]; xj, yj = ring[j][0], ring[j][1]
        if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside

def point_in_geom(lng, lat, geom):
    if geom['type'] == 'Polygon': return point_in_polygon(lng, lat, geom['coordinates'][0])
    elif geom['type'] == 'MultiPolygon': return any(point_in_polygon(lng, lat, p[0]) for p in geom['coordinates'])
    return False

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
    # Download election day roster
    eday_path = os.path.join(DATA_DIR, 'd5_election_day.xlsx')
    print("Downloading election day roster...")
    req = urllib.request.Request(EDAY_URL, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    data = resp.read()
    with open(eday_path, 'wb') as f:
        f.write(data)
    print(f"  ✓ {len(data)/1024:.0f} KB")

    # Extract VUIDs
    eday_vuids = extract_vuids(eday_path)
    print(f"  Election day VUIDs: {len(eday_vuids)}")

    # Import
    conn = sqlite3.connect(DB_PATH)
    before = conn.execute(f"SELECT COUNT(*) FROM voter_elections WHERE election_date='{ELECTION_DATE}'").fetchone()[0]
    for vuid in eday_vuids:
        conn.execute("INSERT OR IGNORE INTO voter_elections (vuid, election_date, election_year, election_type, voting_method, party_voted) VALUES (?, ?, '2026', 'special', 'election-day', '')", (vuid, ELECTION_DATE))
    conn.commit()
    after = conn.execute(f"SELECT COUNT(*) FROM voter_elections WHERE election_date='{ELECTION_DATE}'").fetchone()[0]
    print(f"  Before: {before}, After: {after}, New: {after-before}")

    # Rebuild HD-41 D5 layer
    print("\nRebuilding HD-41 × D5 layer...")
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)
    hd41 = next(f for f in districts['features'] if f['properties'].get('district_id') == 'HD-41')
    hd41_geom = hd41['geometry']

    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT v.vuid, v.lat, v.lng, v.precinct, v.address, v.city, v.zip,
               v.firstname, v.lastname, v.birth_year, v.sex, v.current_party,
               ve.voting_method
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ? AND v.state_house_district = 'HD-41'
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
    """, (ELECTION_DATE,)).fetchall()

    voters = []
    vuids_for_hist = []
    for row in rows:
        if not point_in_geom(row['lng'], row['lat'], hd41_geom):
            continue
        voted_primary = conn.execute("SELECT 1 FROM voter_elections WHERE vuid=? AND election_date='2026-03-03'", (row['vuid'],)).fetchone()
        voted_bond = conn.execute("SELECT 1 FROM voter_elections WHERE vuid=? AND election_date='2026-05-10'", (row['vuid'],)).fetchone()
        vuids_for_hist.append(row['vuid'])
        voters.append({
            'vuid': row['vuid'], 'lat': row['lat'], 'lng': row['lng'],
            'precinct': row['precinct'], 'address': row['address'], 'city': row['city'], 'zip': row['zip'],
            'name': f"{row['firstname'] or ''} {row['lastname'] or ''}".strip(),
            'birth_year': row['birth_year'], 'sex': row['sex'],
            'current_party': row['current_party'] or 'None',
            'voting_method': row['voting_method'],
            'voted_primary': bool(voted_primary),
            'voted_bond': bool(voted_bond),
            'voted_d5': True,
            'hist': [],
        })

    # Voting history
    vuid_to_idx = {v['vuid']: i for i, v in enumerate(voters)}
    chunk_size = 500
    for start in range(0, len(vuids_for_hist), chunk_size):
        chunk = vuids_for_hist[start:start+chunk_size]
        ph = ','.join('?' * len(chunk))
        hist_rows = conn.execute(f"SELECT vuid, election_date, party_voted FROM voter_elections WHERE vuid IN ({ph}) ORDER BY election_date", chunk).fetchall()
        for hr in hist_rows:
            idx = vuid_to_idx.get(hr['vuid'])
            if idx is not None and hr['party_voted']:
                letter = 'D' if 'democrat' in hr['party_voted'].lower() else 'R' if 'republican' in hr['party_voted'].lower() else 'O'
                voters[idx]['hist'].append({'y': (hr['election_date'] or '')[:4], 'p': letter})

    conn.close()

    voted_both = len([v for v in voters if v['voted_primary']])
    d5_only = len([v for v in voters if not v['voted_primary']])

    data = {
        'voters': voters, 'count': len(voters),
        'voted_both_d5_and_primary': voted_both,
        'd5_only_not_primary': d5_only,
        'description': 'McAllen City Commission D5 voters (May 2, 2026) in HD-41. Includes voting history.',
    }
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    print(f"\n✓ {len(voters)} D5 voters in HD-41 ({Path(CACHE_PATH).stat().st_size/1024:.0f} KB)")
    print(f"  Voted both D5 + primary: {voted_both}")
    print(f"  D5 only (skipped primary): {d5_only} ← targets")
    print(f"  Total D5 in DB: {after}")

if __name__ == '__main__':
    main()
