#!/usr/bin/env python3
"""
Import McAllen City Commission District 5 election data (May 2, 2026).
Downloads the cumulative EV roster (April 28 = final) and imports VUIDs.
"""
import urllib.request, sqlite3, os, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DATA_DIR = '/opt/whovoted/data'
DISTRICTS_PATH = '/opt/whovoted/public/data/districts.json'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_d5_voters.json'

# Final cumulative EV roster (has all early voters)
EV_URL = 'https://www.mcallen.net/docs/default-source/cityelections/2026-Special-Election/cumulative-4-28-26.xlsx?sfvrsn=0'
# Mail ballots (already downloaded)
MAIL_PATH = os.path.join(DATA_DIR, 'd5_mail_ballots.xlsx')

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


def download_ev_roster():
    """Download the final cumulative EV roster."""
    outpath = os.path.join(DATA_DIR, 'd5_ev_cumulative_final.xlsx')
    if os.path.exists(outpath) and os.path.getsize(outpath) > 1000:
        print(f"  Already have EV roster ({os.path.getsize(outpath)/1024:.0f} KB)")
        return outpath
    print(f"  Downloading cumulative EV roster (April 28)...")
    req = urllib.request.Request(EV_URL, headers={'User-Agent': 'Mozilla/5.0'})
    resp = urllib.request.urlopen(req, timeout=30)
    data = resp.read()
    if data[:5] == b'<html' or data[:15].startswith(b'<!DOCTYPE'):
        print("  ERROR: Got HTML instead of xlsx")
        return None
    with open(outpath, 'wb') as f:
        f.write(data)
    print(f"  ✓ Downloaded ({len(data)/1024:.0f} KB)")
    return outpath


def extract_vuids_from_xlsx(filepath):
    """Extract VUIDs from an xlsx roster file."""
    import openpyxl
    wb = openpyxl.load_workbook(filepath)
    sheet = wb.active
    
    vuids = set()
    # Scan all rows, all columns for 10-digit numbers (VUIDs)
    for row in sheet.iter_rows(min_row=1, values_only=True):
        for cell in row:
            if cell is None:
                continue
            val = str(cell).strip().replace('.0', '')
            if val.isdigit() and len(val) == 10:
                vuids.add(val)
    
    return vuids


def main():
    print("Importing McAllen City Commission D5 election (May 2, 2026)...\n")
    
    # Step 1: Download EV roster
    print("Step 1: Download rosters")
    ev_path = download_ev_roster()
    
    # Step 2: Extract VUIDs
    print("\nStep 2: Extract VUIDs")
    all_vuids = set()
    
    if ev_path:
        ev_vuids = extract_vuids_from_xlsx(ev_path)
        print(f"  EV roster: {len(ev_vuids)} VUIDs")
        all_vuids.update(ev_vuids)
    
    if os.path.exists(MAIL_PATH):
        mail_vuids = extract_vuids_from_xlsx(MAIL_PATH)
        print(f"  Mail ballots: {len(mail_vuids)} VUIDs")
        all_vuids.update(mail_vuids)
    
    print(f"  Total unique VUIDs: {len(all_vuids)}")
    
    if not all_vuids:
        print("ERROR: No VUIDs extracted")
        return
    
    # Step 3: Import into voter_elections
    print("\nStep 3: Import into database")
    conn = sqlite3.connect(DB_PATH)
    
    # Check how many already exist
    existing = conn.execute(f"SELECT COUNT(*) FROM voter_elections WHERE election_date = '{ELECTION_DATE}'").fetchone()[0]
    print(f"  Existing records for {ELECTION_DATE}: {existing}")
    
    inserted = 0
    for vuid in all_vuids:
        try:
            conn.execute("""
                INSERT OR IGNORE INTO voter_elections (vuid, election_date, election_year, election_type, voting_method, party_voted)
                VALUES (?, ?, '2026', 'special', 'early-voting', '')
            """, (vuid, ELECTION_DATE))
            inserted += 1
        except:
            pass
    
    conn.commit()
    new_total = conn.execute(f"SELECT COUNT(*) FROM voter_elections WHERE election_date = '{ELECTION_DATE}'").fetchone()[0]
    print(f"  Inserted: {inserted} attempts, new total: {new_total}")
    
    # Step 4: Build HD-41 D5 voter layer (D5 voters who are also in HD-41)
    print("\nStep 4: Build HD-41 × D5 voter layer")
    
    # Load HD-41 boundary
    with open(DISTRICTS_PATH) as f:
        districts = json.load(f)
    hd41 = next(f for f in districts['features'] if f['properties'].get('district_id') == 'HD-41')
    hd41_geom = hd41['geometry']
    
    conn.row_factory = sqlite3.Row
    d5_in_hd41 = conn.execute("""
        SELECT v.vuid, v.lat, v.lng, v.precinct, v.address, v.city, v.zip,
               v.firstname, v.lastname, v.birth_year, v.sex, v.current_party
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ?
        AND v.state_house_district = 'HD-41'
        AND v.lat IS NOT NULL AND v.lng IS NOT NULL
    """, (ELECTION_DATE,)).fetchall()
    
    voters = []
    for row in d5_in_hd41:
        if not point_in_geom(row['lng'], row['lat'], hd41_geom):
            continue
        # Check if they also voted in the March primary
        voted_primary = conn.execute(
            "SELECT 1 FROM voter_elections WHERE vuid = ? AND election_date = '2026-03-03'",
            (row['vuid'],)
        ).fetchone()
        
        voters.append({
            'vuid': row['vuid'],
            'lat': row['lat'], 'lng': row['lng'],
            'precinct': row['precinct'],
            'address': row['address'], 'city': row['city'], 'zip': row['zip'],
            'name': f"{row['firstname'] or ''} {row['lastname'] or ''}".strip(),
            'birth_year': row['birth_year'], 'sex': row['sex'],
            'current_party': row['current_party'] or 'None',
            'voted_primary': bool(voted_primary),
        })
    
    conn.close()
    
    # Stats
    voted_both = len([v for v in voters if v['voted_primary']])
    d5_only = len([v for v in voters if not v['voted_primary']])
    
    data = {
        'voters': voters,
        'count': len(voters),
        'voted_both_d5_and_primary': voted_both,
        'd5_only_not_primary': d5_only,
        'description': 'McAllen City Commission D5 voters (May 2, 2026) who are in HD-41',
    }
    
    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    
    print(f"\n✓ {len(voters)} D5 voters in HD-41 ({Path(CACHE_PATH).stat().st_size/1024:.0f} KB)")
    print(f"  Voted in both D5 + March primary: {voted_both}")
    print(f"  D5 only (skipped primary): {d5_only} ← mobilization targets")


if __name__ == '__main__':
    main()
