#!/usr/bin/env python3
"""
Generate precinct-level report card for HD-41 — DUAL RACE analysis.

Tracks both the Democratic runoff (Salinas vs Haddad) and the Republican
runoff (Sanchez vs Groves) precinct by precinct. For each precinct, shows:
- Total registered voters
- How many pulled Dem ballots vs Rep ballots
- Turnout rate for each party
- Which precincts are strongholds vs battlegrounds
- March primary comparison (who came back, who didn't)
"""
import sqlite3, json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_reportcard.json'
ELECTION_DATE = '2026-05-26'  # Runoff
MARCH_PRIMARY = '2026-03-03'  # Original primary
DISTRICT = 'HD-41'


def grade(turnout_pct):
    """Grade based on runoff turnout."""
    if turnout_pct >= 20.0: return 'A'
    if turnout_pct >= 14.0: return 'B'
    if turnout_pct >= 9.0: return 'C'
    if turnout_pct >= 5.0: return 'D'
    return 'F'


def main():
    print(f"Generating dual-race precinct report card for {DISTRICT}...")

    conn = sqlite3.connect(DB_PATH)

    # ── Runoff data: precinct × party ──
    runoff_rows = conn.execute("""
        SELECT v.precinct,
               COUNT(DISTINCT v.vuid) as registered,
               COUNT(DISTINCT CASE WHEN ve.vuid IS NOT NULL THEN v.vuid END) as voted,
               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN v.vuid END) as dem,
               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN v.vuid END) as rep,
               AVG(v.lat) as lat,
               AVG(v.lng) as lng
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.state_house_district = ?
        AND v.precinct IS NOT NULL
        GROUP BY v.precinct
        ORDER BY v.precinct
    """, (ELECTION_DATE, DISTRICT)).fetchall()

    # ── March primary data for comparison ──
    march_rows = conn.execute("""
        SELECT v.precinct,
               COUNT(DISTINCT CASE WHEN ve.vuid IS NOT NULL THEN v.vuid END) as voted,
               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN v.vuid END) as dem,
               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN v.vuid END) as rep
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.state_house_district = ?
        AND v.precinct IS NOT NULL
        GROUP BY v.precinct
    """, (MARCH_PRIMARY, DISTRICT)).fetchall()
    march_data = {r[0]: {'voted': r[1], 'dem': r[2], 'rep': r[3]} for r in march_rows}

    # ── Runoff voters who also voted in March (returnees) ──
    returnee_rows = conn.execute("""
        SELECT v.precinct, ve_runoff.party_voted,
               COUNT(DISTINCT v.vuid) as cnt
        FROM voters v
        INNER JOIN voter_elections ve_runoff ON v.vuid = ve_runoff.vuid AND ve_runoff.election_date = ?
        INNER JOIN voter_elections ve_march ON v.vuid = ve_march.vuid AND ve_march.election_date = ?
        WHERE v.state_house_district = ? AND v.precinct IS NOT NULL
        GROUP BY v.precinct, ve_runoff.party_voted
    """, (ELECTION_DATE, MARCH_PRIMARY, DISTRICT)).fetchall()
    returnees = {}
    for pct, party, cnt in returnee_rows:
        if pct not in returnees:
            returnees[pct] = {'dem_returnees': 0, 'rep_returnees': 0}
        if party == 'Democratic':
            returnees[pct]['dem_returnees'] = cnt
        elif party == 'Republican':
            returnees[pct]['rep_returnees'] = cnt

    conn.close()

    # ── Build report ──
    precincts = []
    total_reg = 0
    total_voted = 0
    total_dem = 0
    total_rep = 0

    for row in runoff_rows:
        precinct, reg, voted, dem, rep, lat, lng = row
        turnout = (voted / reg * 100) if reg > 0 else 0
        dem_pct = (dem / reg * 100) if reg > 0 else 0
        rep_pct = (rep / reg * 100) if reg > 0 else 0
        dem_share = (dem / voted * 100) if voted > 0 else 0
        rep_share = (rep / voted * 100) if voted > 0 else 0

        # March comparison
        march = march_data.get(precinct, {'voted': 0, 'dem': 0, 'rep': 0})
        march_dem = march['dem']
        march_rep = march['rep']
        dem_retention = round(dem / march_dem * 100, 1) if march_dem > 0 else 0
        rep_retention = round(rep / march_rep * 100, 1) if march_rep > 0 else 0
        dem_dropoff = march_dem - dem
        rep_dropoff = march_rep - rep

        # Returnees
        ret = returnees.get(precinct, {'dem_returnees': 0, 'rep_returnees': 0})

        # Classify precinct
        if dem_share >= 70:
            lean = 'Strong D'
        elif dem_share >= 55:
            lean = 'Lean D'
        elif rep_share >= 70:
            lean = 'Strong R'
        elif rep_share >= 55:
            lean = 'Lean R'
        else:
            lean = 'Competitive'

        total_reg += reg
        total_voted += voted
        total_dem += dem
        total_rep += rep

        precincts.append({
            'precinct': precinct,
            'name': f'Precinct {precinct}',
            'lat': round(lat, 4) if lat else None,
            'lng': round(lng, 4) if lng else None,
            'registered': reg,
            'voted': voted,
            'not_voted': reg - voted,
            'turnout_pct': round(turnout, 2),
            'grade': grade(turnout),
            'lean': lean,
            # Democratic race
            'dem': dem,
            'dem_pct_of_reg': round(dem_pct, 2),
            'dem_share': round(dem_share, 1),
            'march_dem': march_dem,
            'dem_retention': dem_retention,
            'dem_dropoff': dem_dropoff,
            'dem_returnees': ret['dem_returnees'],
            'dem_new': dem - ret['dem_returnees'],
            # Republican race
            'rep': rep,
            'rep_pct_of_reg': round(rep_pct, 2),
            'rep_share': round(rep_share, 1),
            'march_rep': march_rep,
            'rep_retention': rep_retention,
            'rep_dropoff': rep_dropoff,
            'rep_returnees': ret['rep_returnees'],
            'rep_new': rep - ret['rep_returnees'],
        })

    overall_turnout = (total_voted / total_reg * 100) if total_reg > 0 else 0
    overall_dem_share = (total_dem / total_voted * 100) if total_voted > 0 else 0

    # ── Identify strategic precincts ──
    sorted_by_dem = sorted(precincts, key=lambda p: p['dem'], reverse=True)
    sorted_by_rep = sorted(precincts, key=lambda p: p['rep'], reverse=True)
    sorted_by_dem_dropoff = sorted(precincts, key=lambda p: p['dem_dropoff'], reverse=True)
    sorted_by_rep_dropoff = sorted(precincts, key=lambda p: p['rep_dropoff'], reverse=True)
    competitive = [p for p in precincts if p['lean'] == 'Competitive']

    data = {
        'districts': precincts,
        'summary': {
            'total_registered': total_reg,
            'total_voted': total_voted,
            'total_not_voted': total_reg - total_voted,
            'overall_turnout_pct': round(overall_turnout, 2),
            'overall_grade': grade(overall_turnout),
            'total_dem': total_dem,
            'total_rep': total_rep,
            'dem_share': round(overall_dem_share, 1),
            'rep_share': round(100 - overall_dem_share, 1),
        },
        # Strategic intel
        'dem_strongholds': [p['precinct'] for p in precincts if p['lean'] == 'Strong D'][:10],
        'rep_strongholds': [p['precinct'] for p in precincts if p['lean'] == 'Strong R'][:10],
        'competitive_precincts': [p['precinct'] for p in competitive][:10],
        'dem_biggest_dropoff': [{'pct': p['precinct'], 'dropoff': p['dem_dropoff'], 'march': p['march_dem']} for p in sorted_by_dem_dropoff[:5]],
        'rep_biggest_dropoff': [{'pct': p['precinct'], 'dropoff': p['rep_dropoff'], 'march': p['march_rep']} for p in sorted_by_rep_dropoff[:5]],
        'dem_top_precincts': [{'pct': p['precinct'], 'dem': p['dem'], 'turnout': p['dem_pct_of_reg']} for p in sorted_by_dem[:5]],
        'rep_top_precincts': [{'pct': p['precinct'], 'rep': p['rep'], 'turnout': p['rep_pct_of_reg']} for p in sorted_by_rep[:5]],
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(data, f, separators=(',', ':'))

    print(f"\nOverall: {total_voted}/{total_reg} = {overall_turnout:.2f}%")
    print(f"Dem: {total_dem} ({overall_dem_share:.1f}%) | Rep: {total_rep} ({100-overall_dem_share:.1f}%)")
    print(f"Precincts: {len(precincts)} | Competitive: {len(competitive)}")
    print(f"Dem strongholds: {len([p for p in precincts if p['lean']=='Strong D'])}")
    print(f"Rep strongholds: {len([p for p in precincts if p['lean']=='Strong R'])}")

if __name__ == '__main__':
    main()
