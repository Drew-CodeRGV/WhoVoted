#!/usr/bin/env python3
"""
Parse the official Hidalgo County canvass PDFs for HD-41 State Representative race.

PDF format (per precinct, per race):
  Line: "001                    92 of 1,016 registered voters = 9.06%"  ← precinct header
  ...
  Line: "State Representative, District 41 - Democratic Party"  ← race header
  Line: "Choice                Party  Absentee Voting  Early Voting  Election Day  Total"
  Line: "Victor 'Seby' Haddad    2  25.00%    83  30.86%    29  30.85%    114  30.73%"
  Line: "Julio Salinas           2  25.00%   119  44.24%    57  60.64%    178  47.98%"
  Line: "Eric Holguín            4  50.00%    67  24.91%     8   8.51%     79  21.29%"
  Line: "                     Cast Votes:  8  100.00%  269  100.00%  94  100.00%  371  100.00%"

Strategy:
1. Scan for precinct headers (lines with "registered voters")
2. Track current precinct
3. When we hit "State Representative, District 41", extract candidate votes
4. The TOTAL column (last number) is what we want
"""
import re, json, sqlite3
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
DEM_TEXT = '/opt/whovoted/data/hidalgo_dem_results_text.txt'
REP_TEXT = '/opt/whovoted/data/hidalgo_rep_results_text.txt'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_primary_candidates.json'

DEM_PDF_URL = 'https://www.hidalgocounty.us/DocumentCenter/View/72302/Democrat-Precinct-Results'
REP_PDF_URL = 'https://www.hidalgocounty.us/DocumentCenter/View/72303/Republican-Precinct-Results'


def parse_canvass(text_path, party, race_name='State Representative, District 41'):
    """Parse precinct-by-precinct results for a specific race."""
    with open(text_path) as f:
        lines = f.readlines()

    results = {}  # precinct -> {candidate: total_votes}
    current_precinct = None
    in_race = False
    skip_header = False

    for i, line in enumerate(lines):
        raw = line.rstrip('\n')

        # Detect precinct header: "001    92 of 1,016 registered voters = 9.06%"
        m = re.match(r'^(\d{3})\s+.*registered voters', raw)
        if m:
            current_precinct = m.group(1)
            in_race = False
            continue

        # Detect race start
        if race_name in raw and party.lower() in raw.lower():
            in_race = True
            skip_header = True  # next line is column headers
            continue

        if not in_race or not current_precinct:
            continue

        # Skip the "Choice  Party  Absentee..." header line
        if skip_header:
            if 'Choice' in raw or 'Party' in raw:
                skip_header = False
                continue
            skip_header = False

        # Detect end of race (Cast Votes line or blank followed by next race)
        if 'Cast Votes' in raw or 'Undervotes' in raw or 'Overvotes' in raw:
            in_race = False
            continue

        # Skip blank lines
        if not raw.strip():
            in_race = False
            continue

        # Parse candidate line
        # Format: "Victor 'Seby' Haddad    2  25.00%    83  30.86%    29  30.85%    114  30.73%"
        # We want the candidate name and the LAST number (Total votes)
        # Numbers appear as: count  percentage%  count  percentage%  ...  total_count  total_pct%
        numbers = re.findall(r'(\d+)\s+[\d.]+%', raw)
        if numbers and len(numbers) >= 1:
            # The last number before a percentage is the Total
            total_votes = int(numbers[-1])

            # Extract candidate name (everything before the first number)
            name_match = re.match(r'^(.+?)\s+\d', raw)
            if name_match:
                candidate_name = name_match.group(1).strip()
                # Clean up name
                candidate_name = re.sub(r'\s+', ' ', candidate_name)

                if current_precinct not in results:
                    results[current_precinct] = {}
                results[current_precinct][candidate_name] = total_votes

    return results


def main():
    print("Parsing official Hidalgo County canvass for HD-41...\n")

    # Check text files exist
    if not Path(DEM_TEXT).exists() or not Path(REP_TEXT).exists():
        print("ERROR: Text files not found. Run import_hd41_canvass.py first to download and extract PDFs.")
        return

    # Parse both parties
    print("Parsing Democratic results...")
    dem_results = parse_canvass(DEM_TEXT, 'Democratic')
    print(f"  Found {len(dem_results)} precincts")

    print("Parsing Republican results...")
    rep_results = parse_canvass(REP_TEXT, 'Republican')
    print(f"  Found {len(rep_results)} precincts")

    # Show results
    if dem_results:
        # Get candidate names from first precinct
        first_pct = next(iter(dem_results.values()))
        dem_candidates = list(first_pct.keys())
        print(f"\n  Dem candidates: {dem_candidates}")
        # Show first 5 precincts
        for pct in list(dem_results.keys())[:5]:
            print(f"    Pct {pct}: {dem_results[pct]}")
        # Totals
        totals = {}
        for pct_data in dem_results.values():
            for c, v in pct_data.items():
                totals[c] = totals.get(c, 0) + v
        print(f"  District totals: {totals}")
    else:
        dem_candidates = []

    if rep_results:
        first_pct = next(iter(rep_results.values()))
        rep_candidates = list(first_pct.keys())
        print(f"\n  Rep candidates: {rep_candidates}")
        for pct in list(rep_results.keys())[:5]:
            print(f"    Pct {pct}: {rep_results[pct]}")
        totals = {}
        for pct_data in rep_results.values():
            for c, v in pct_data.items():
                totals[c] = totals.get(c, 0) + v
        print(f"  District totals: {totals}")
    else:
        rep_candidates = []

    if not dem_results and not rep_results:
        print("\nERROR: No results parsed. Check text file format.")
        return

    # Save to DB
    print("\nSaving to database...")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM hd41_candidate_results WHERE election_date='2026-03-03'")

    inserted = 0
    for pct, votes in dem_results.items():
        for candidate, count in votes.items():
            conn.execute("""INSERT INTO hd41_candidate_results (election_date, party, candidate, precinct, votes)
                VALUES ('2026-03-03', 'Democratic', ?, ?, ?)""", (candidate, pct, count))
            inserted += 1
    for pct, votes in rep_results.items():
        for candidate, count in votes.items():
            conn.execute("""INSERT INTO hd41_candidate_results (election_date, party, candidate, precinct, votes)
                VALUES ('2026-03-03', 'Republican', ?, ?, ?)""", (candidate, pct, count))
            inserted += 1
    conn.commit()
    print(f"  ✓ Inserted {inserted} rows")

    # Build cache
    print("\nBuilding candidate cache...")
    centroids = {}
    for pct, lat, lng, voters in conn.execute("""
        SELECT precinct, AVG(lat), AVG(lng), COUNT(*)
        FROM voters WHERE state_house_district='HD-41' AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """).fetchall():
        norm = pct.lstrip('0') or '0'
        if '.' in pct:
            norm = pct.split('.')[0].lstrip('0') or '0'
        centroids[norm] = {'lat': round(lat, 4), 'lng': round(lng, 4), 'registered': voters}
        centroids[pct] = centroids[norm]
    conn.close()

    # Build analysis
    all_candidates = {}
    for party, results, cands in [('Democratic', dem_results, dem_candidates), ('Republican', rep_results, rep_candidates)]:
        party_total = {}
        for pct_data in results.values():
            for c, v in pct_data.items():
                party_total[c] = party_total.get(c, 0) + v
        grand_total = sum(party_total.values())

        for candidate in cands:
            total = party_total.get(candidate, 0)
            precinct_data = []
            for pct, votes in results.items():
                my_votes = votes.get(candidate, 0)
                pct_total = sum(votes.values())
                share = round(my_votes / pct_total * 100, 1) if pct_total > 0 else 0
                beaten_by = [{'candidate': c, 'votes': v, 'share': round(v/pct_total*100, 1)}
                             for c, v in votes.items() if c != candidate and v > my_votes]
                centroid = centroids.get(pct, centroids.get(pct.lstrip('0'), {}))
                precinct_data.append({
                    'precinct': pct, 'votes': my_votes, 'pct_total': pct_total,
                    'share': share, 'lat': centroid.get('lat'), 'lng': centroid.get('lng'),
                    'registered': centroid.get('registered', 0), 'beaten_by': beaten_by,
                })
            precinct_data.sort(key=lambda x: x['share'], reverse=True)

            all_candidates[candidate] = {
                'party': party, 'total_votes': total,
                'district_share': round(total / grand_total * 100, 1) if grand_total else 0,
                'precincts': precinct_data,
                'strong_precincts': len([p for p in precinct_data if p['share'] >= 50]),
                'weak_precincts': len([p for p in precinct_data if p['share'] < 25]),
            }

    output = {
        'election_date': '2026-03-03',
        'district': 'HD-41',
        'source': 'Hidalgo County Official Canvass — Precinct-by-Precinct Results',
        'source_urls': {'Democratic': DEM_PDF_URL, 'Republican': REP_PDF_URL},
        'dem_candidates': dem_candidates,
        'rep_candidates': rep_candidates,
        'candidates': all_candidates,
    }

    with open(CACHE_PATH, 'w') as f:
        json.dump(output, f, separators=(',', ':'))
    print(f"  ✓ Cache: {Path(CACHE_PATH).stat().st_size/1024:.0f} KB")
    for c, d in all_candidates.items():
        print(f"    {c} ({d['party']}): {d['total_votes']} votes ({d['district_share']}%) — strong:{d['strong_precincts']} weak:{d['weak_precincts']}")


if __name__ == '__main__':
    main()
