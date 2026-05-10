#!/usr/bin/env python3
"""
Update HD-41 candidate results with REAL certified district-wide totals.

Source: Texas SOS / branch.vote certified results
https://branch.vote/races/2026-texas-primary-election-tx-state-state-representative-tx-state-house-41-d
https://branch.vote/races/2026-texas-primary-election-tx-state-state-representative-tx-state-house-41-r

Democratic Primary (15,562 total votes):
  Julio Salinas:        6,004 votes (38.6%)
  Victor "Seby" Haddad: 5,805 votes (37.3%)
  Eric Holguin:         3,753 votes (24.1%)

Republican Primary (6,207 total votes):
  Sergio Sanchez:       2,840 votes (45.8%)
  Gary Groves:          2,385 votes (38.4%)
  Sarah Sagredo-Hammond:  982 votes (15.8%)

NOTE: We do NOT have precinct-level candidate results from the SOS.
The per-precinct splits are ESTIMATED by applying district-wide ratios
to each precinct's known party total. This is the best available
approximation until the county publishes the official canvass with
precinct-by-precinct candidate breakdowns.

The PARTY totals per precinct (how many pulled Dem vs Rep ballots) ARE
real data from the voter rolls. Only the within-party candidate split
is estimated.
"""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_primary_candidates.json'

# REAL certified results
DEM_RESULTS = {
    'Julio Salinas': {'votes': 6004, 'pct': 38.6},
    'Victor Haddad': {'votes': 5805, 'pct': 37.3},
    'Eric Holguin': {'votes': 3753, 'pct': 24.1},
}
REP_RESULTS = {
    'Sergio Sanchez': {'votes': 2840, 'pct': 45.8},
    'Gary Groves': {'votes': 2385, 'pct': 38.4},
    'Sarah Sagredo-Hammond': {'votes': 982, 'pct': 15.8},
}

DEM_TOTAL = sum(r['votes'] for r in DEM_RESULTS.values())  # 15,562
REP_TOTAL = sum(r['votes'] for r in REP_RESULTS.values())  # 6,207

DEM_CANDIDATES = list(DEM_RESULTS.keys())
REP_CANDIDATES = list(REP_RESULTS.keys())


def main():
    conn = sqlite3.connect(DB_PATH)

    # Clear old estimated data
    conn.execute("DELETE FROM hd41_candidate_results WHERE election_date = '2026-03-03'")
    conn.commit()
    print("Cleared old estimates")

    # Get per-precinct party totals (REAL data from voter rolls)
    rows = conn.execute("""
        SELECT ve.precinct, ve.party_voted, COUNT(*) as votes
        FROM voter_elections ve
        WHERE ve.election_date = '2026-03-03'
        AND ve.state_house_district = 'HD-41'
        AND ve.precinct IS NOT NULL
        AND ve.party_voted IN ('Democratic', 'Republican')
        GROUP BY ve.precinct, ve.party_voted
    """).fetchall()

    print(f"Found {len(rows)} precinct×party combinations")

    # Apply certified district-wide ratios to each precinct
    inserted = 0
    for precinct, party, pct_votes in rows:
        if party == 'Democratic':
            candidates = DEM_RESULTS
            district_total = DEM_TOTAL
        else:
            candidates = REP_RESULTS
            district_total = REP_TOTAL

        # Distribute this precinct's votes proportionally
        remaining = pct_votes
        items = list(candidates.items())
        for i, (candidate, result) in enumerate(items):
            share = result['votes'] / district_total
            if i == len(items) - 1:
                votes = remaining  # last gets remainder to avoid rounding errors
            else:
                votes = round(pct_votes * share)
                remaining -= votes

            conn.execute("""
                INSERT INTO hd41_candidate_results (election_date, party, candidate, precinct, votes)
                VALUES ('2026-03-03', ?, ?, ?, ?)
            """, (party, candidate, precinct, votes))
            inserted += 1

    conn.commit()
    print(f"Inserted {inserted} rows with real district-wide ratios")

    # Verify totals match
    for party, expected_results in [('Democratic', DEM_RESULTS), ('Republican', REP_RESULTS)]:
        for candidate, expected in expected_results.items():
            actual = conn.execute("""
                SELECT SUM(votes) FROM hd41_candidate_results
                WHERE candidate = ? AND election_date = '2026-03-03'
            """, (candidate,)).fetchone()[0] or 0
            diff = abs(actual - expected['votes'])
            status = '✓' if diff <= 5 else '⚠️'  # allow small rounding diff
            print(f"  {status} {candidate}: expected {expected['votes']}, got {actual} (diff: {diff})")

    # Now rebuild the cache
    print("\nRebuilding candidate analysis cache...")
    build_cache(conn)
    conn.close()


def build_cache(conn):
    """Build the candidate analysis cache for the frontend."""
    results = conn.execute("""
        SELECT party, candidate, precinct, votes
        FROM hd41_candidate_results WHERE election_date = '2026-03-03'
        ORDER BY party, candidate, precinct
    """).fetchall()

    centroids = {}
    for pct, lat, lng, voters in conn.execute("""
        SELECT precinct, AVG(lat), AVG(lng), COUNT(*)
        FROM voters WHERE state_house_district='HD-41' AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """).fetchall():
        centroids[pct] = {'lat': round(lat, 4), 'lng': round(lng, 4), 'registered': voters}

    candidates = {}
    for party, candidate, precinct, votes in results:
        if candidate not in candidates:
            candidates[candidate] = {'party': party, 'total_votes': 0, 'precincts': {}}
        candidates[candidate]['total_votes'] += votes
        candidates[candidate]['precincts'][precinct] = votes

    candidate_analysis = {}
    for candidate, data in candidates.items():
        party = data['party']
        total = data['total_votes']
        same_party = {c: d for c, d in candidates.items() if d['party'] == party}
        party_total_by_pct = {}
        for c, d in same_party.items():
            for pct, votes in d['precincts'].items():
                party_total_by_pct[pct] = party_total_by_pct.get(pct, 0) + votes

        precinct_results = []
        for pct, votes in data['precincts'].items():
            pct_total = party_total_by_pct.get(pct, 1)
            pct_share = round(votes / pct_total * 100, 1) if pct_total > 0 else 0
            centroid = centroids.get(pct, {})
            beaten_by = []
            for other_c, other_d in same_party.items():
                if other_c != candidate:
                    other_votes = other_d['precincts'].get(pct, 0)
                    if other_votes > votes:
                        beaten_by.append({'candidate': other_c, 'votes': other_votes,
                                          'share': round(other_votes / pct_total * 100, 1)})
            precinct_results.append({
                'precinct': pct, 'votes': votes, 'pct_total': pct_total,
                'share': pct_share, 'lat': centroid.get('lat'), 'lng': centroid.get('lng'),
                'registered': centroid.get('registered', 0), 'beaten_by': beaten_by,
            })

        precinct_results.sort(key=lambda x: x['share'], reverse=True)
        strong = [p for p in precinct_results if p['share'] >= 50]
        weak = [p for p in precinct_results if p['share'] < 30]
        weak.sort(key=lambda x: x['share'])

        candidate_analysis[candidate] = {
            'party': party, 'total_votes': total,
            'district_share': round(total / sum(d['total_votes'] for d in same_party.values()) * 100, 1),
            'precincts': precinct_results,
            'strong_precincts': len(strong), 'weak_precincts': len(weak),
            'top_5': precinct_results[:5],
            'bottom_5': precinct_results[-5:] if len(precinct_results) >= 5 else precinct_results,
        }

    output = {
        'election_date': '2026-03-03',
        'district': 'HD-41',
        'note': 'District-wide totals are CERTIFIED (TX SOS). Per-precinct candidate splits are estimated from district-wide ratios applied to real per-precinct party totals.',
        'certified_results': {
            'Democratic': DEM_RESULTS,
            'Republican': REP_RESULTS,
            'dem_total': DEM_TOTAL,
            'rep_total': REP_TOTAL,
        },
        'dem_candidates': DEM_CANDIDATES,
        'rep_candidates': REP_CANDIDATES,
        'candidates': candidate_analysis,
        'precinct_centroids': centroids,
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    print(f"✓ Cache: {Path(CACHE_PATH).stat().st_size / 1024:.0f} KB")
    for c, d in candidate_analysis.items():
        print(f"  {c} ({d['party']}): {d['total_votes']} votes ({d['district_share']}%)")


if __name__ == '__main__':
    main()
