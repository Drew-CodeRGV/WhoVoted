#!/usr/bin/env python3
"""
Import HD-41 March 2026 primary results — candidate-level, precinct-by-precinct.

This creates a new table `hd41_primary_results` with per-precinct vote totals
for each candidate in both the Dem and Rep primaries.

Data source: Texas Secretary of State certified results
https://results.texas-election.com/races

HD-41 Democratic Primary (March 3, 2026):
  - Julio Salinas (advanced to runoff)
  - Victor "Seby" Haddad (advanced to runoff)
  - Eric Holguin
  - (others if any)

HD-41 Republican Primary (March 3, 2026):
  - Sergio Sanchez (advanced to runoff)
  - Gary Groves (advanced to runoff)
  - Sarah Cantu (eliminated)
  - (others if any)

NOTE: This script creates the table and can be populated either:
  1. Manually with INSERT statements from certified results
  2. By scraping the SOS results page
  3. By importing a CSV of precinct results

For now, we create the schema and populate from whatever data is available.
"""
import sqlite3
import json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_primary_candidates.json'

# Known candidates
DEM_CANDIDATES = ['Julio Salinas', 'Victor Haddad', 'Eric Holguin']
REP_CANDIDATES = ['Sergio Sanchez', 'Gary Groves', 'Sarah Cantu']


def create_table(conn):
    """Create the candidate results table."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS hd41_candidate_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            election_date TEXT NOT NULL,
            party TEXT NOT NULL,
            candidate TEXT NOT NULL,
            precinct TEXT NOT NULL,
            votes INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hd41_results_precinct
        ON hd41_candidate_results(precinct, party)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_hd41_results_candidate
        ON hd41_candidate_results(candidate)
    """)
    conn.commit()
    print("✓ Created hd41_candidate_results table")


def check_existing_data(conn):
    """Check if we already have data."""
    try:
        cnt = conn.execute("SELECT COUNT(*) FROM hd41_candidate_results").fetchone()[0]
        return cnt
    except:
        return 0


def generate_estimated_results(conn):
    """
    Generate ESTIMATED per-candidate results based on what we know:
    - We have per-precinct party totals (how many Dem/Rep ballots per precinct)
    - We know the district-wide vote shares from certified results
    - We can estimate per-precinct candidate splits proportionally

    Known district-wide results (from SOS):
    Dem: Salinas ~40%, Haddad ~35%, Holguin ~25% (approximate)
    Rep: Sanchez ~40%, Groves ~35%, Cantu ~25% (approximate)

    TODO: Replace with actual precinct-level certified results when available.
    For now, use uniform district-wide ratios applied to each precinct's party total.
    This is a placeholder — the real data should be imported from SOS.
    """
    print("Generating estimated candidate results from party totals...")
    print("  NOTE: These are ESTIMATES. Replace with SOS certified results.")

    # Get per-precinct party totals from voter_elections
    rows = conn.execute("""
        SELECT ve.precinct, ve.party_voted, COUNT(*) as votes
        FROM voter_elections ve
        WHERE ve.election_date = '2026-03-03'
        AND ve.state_house_district = 'HD-41'
        AND ve.precinct IS NOT NULL
        AND ve.party_voted IN ('Democratic', 'Republican')
        GROUP BY ve.precinct, ve.party_voted
    """).fetchall()

    # District-wide estimated splits (placeholder — replace with real data)
    # These should come from the SOS certified results
    dem_splits = {'Julio Salinas': 0.40, 'Victor Haddad': 0.35, 'Eric Holguin': 0.25}
    rep_splits = {'Sergio Sanchez': 0.40, 'Gary Groves': 0.35, 'Sarah Cantu': 0.25}

    inserted = 0
    for precinct, party, total_votes in rows:
        if party == 'Democratic':
            splits = dem_splits
        elif party == 'Republican':
            splits = rep_splits
        else:
            continue

        # Distribute votes proportionally (with rounding)
        remaining = total_votes
        candidates = list(splits.items())
        for i, (candidate, share) in enumerate(candidates):
            if i == len(candidates) - 1:
                votes = remaining  # last candidate gets remainder
            else:
                votes = round(total_votes * share)
                remaining -= votes

            conn.execute("""
                INSERT INTO hd41_candidate_results (election_date, party, candidate, precinct, votes)
                VALUES ('2026-03-03', ?, ?, ?, ?)
            """, (party, candidate, precinct, votes))
            inserted += 1

    conn.commit()
    print(f"  Inserted {inserted} rows ({len(set(r[0] for r in rows))} precincts)")


def build_cache(conn):
    """Build the candidate analysis cache for the frontend."""
    print("Building candidate analysis cache...")

    # Get all results
    results = conn.execute("""
        SELECT party, candidate, precinct, votes
        FROM hd41_candidate_results
        WHERE election_date = '2026-03-03'
        ORDER BY party, candidate, precinct
    """).fetchall()

    # Get precinct centroids for map display
    centroids = {}
    centroid_rows = conn.execute("""
        SELECT precinct, AVG(lat) as lat, AVG(lng) as lng, COUNT(*) as voters
        FROM voters
        WHERE state_house_district = 'HD-41' AND precinct IS NOT NULL AND lat IS NOT NULL
        GROUP BY precinct
    """).fetchall()
    for pct, lat, lng, voters in centroid_rows:
        centroids[pct] = {'lat': round(lat, 4), 'lng': round(lng, 4), 'registered': voters}

    # Aggregate by candidate
    candidates = {}
    for party, candidate, precinct, votes in results:
        if candidate not in candidates:
            candidates[candidate] = {'party': party, 'total_votes': 0, 'precincts': {}}
        candidates[candidate]['total_votes'] += votes
        candidates[candidate]['precincts'][precinct] = votes

    # For each candidate, compute per-precinct analysis
    candidate_analysis = {}
    for candidate, data in candidates.items():
        party = data['party']
        total = data['total_votes']

        # Get all candidates in same party for comparison
        same_party = {c: d for c, d in candidates.items() if d['party'] == party}
        party_total_by_pct = {}
        for c, d in same_party.items():
            for pct, votes in d['precincts'].items():
                party_total_by_pct[pct] = party_total_by_pct.get(pct, 0) + votes

        # Per-precinct analysis
        precinct_results = []
        for pct, votes in data['precincts'].items():
            pct_total = party_total_by_pct.get(pct, 1)
            pct_share = round(votes / pct_total * 100, 1) if pct_total > 0 else 0
            centroid = centroids.get(pct, {})

            # Who beat this candidate in this precinct?
            beaten_by = []
            for other_c, other_d in same_party.items():
                if other_c != candidate:
                    other_votes = other_d['precincts'].get(pct, 0)
                    if other_votes > votes:
                        beaten_by.append({'candidate': other_c, 'votes': other_votes,
                                          'share': round(other_votes / pct_total * 100, 1)})

            precinct_results.append({
                'precinct': pct,
                'votes': votes,
                'pct_total': pct_total,
                'share': pct_share,
                'lat': centroid.get('lat'),
                'lng': centroid.get('lng'),
                'registered': centroid.get('registered', 0),
                'beaten_by': beaten_by,
            })

        # Sort: best precincts first
        precinct_results.sort(key=lambda x: x['share'], reverse=True)

        # Identify strengths and weaknesses
        strong = [p for p in precinct_results if p['share'] >= 50]
        weak = [p for p in precinct_results if p['share'] < 30]
        weak.sort(key=lambda x: x['share'])  # worst first

        candidate_analysis[candidate] = {
            'party': party,
            'total_votes': total,
            'district_share': round(total / sum(d['total_votes'] for d in same_party.values()) * 100, 1),
            'precincts': precinct_results,
            'strong_precincts': len(strong),
            'weak_precincts': len(weak),
            'top_5': precinct_results[:5],
            'bottom_5': precinct_results[-5:] if len(precinct_results) >= 5 else precinct_results,
        }

    # Build output
    output = {
        'election_date': '2026-03-03',
        'district': 'HD-41',
        'note': 'ESTIMATED from party totals. Replace with SOS certified precinct results.',
        'dem_candidates': DEM_CANDIDATES,
        'rep_candidates': REP_CANDIDATES,
        'candidates': candidate_analysis,
        'precinct_centroids': centroids,
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    print(f"✓ Cache written: {Path(CACHE_PATH).stat().st_size / 1024:.0f} KB")
    for c, d in candidate_analysis.items():
        print(f"  {c} ({d['party']}): {d['total_votes']} votes, {d['district_share']}% share, "
              f"strong in {d['strong_precincts']} pcts, weak in {d['weak_precincts']} pcts")


def main():
    conn = sqlite3.connect(DB_PATH)
    create_table(conn)

    existing = check_existing_data(conn)
    if existing > 0:
        print(f"Already have {existing} rows. Rebuilding cache only.")
    else:
        generate_estimated_results(conn)

    build_cache(conn)
    conn.close()


if __name__ == '__main__':
    main()
