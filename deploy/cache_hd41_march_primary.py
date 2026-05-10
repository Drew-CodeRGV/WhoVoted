#!/usr/bin/env python3
"""
Cache the March 3, 2026 primary results for HD-41.

This is the FIRST ROUND data — the election that sent both races to a runoff.
Results: No candidate got >50% in either party.
  Dem: Julio Salinas (led) vs Victor "Seby" Haddad (2nd) — advanced to runoff
  Rep: Sergio Sanchez (led) vs Gary Groves (2nd) — advanced to runoff

This cache provides:
- Full voter list from March primary (who voted, which party)
- Precinct-by-precinct party breakdown
- Demographics of March voters
- Identifies March voters who have NOT yet returned for the runoff (mobilization targets)
"""
import sqlite3, json
from pathlib import Path
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_march_primary.json'
MARCH_DATE = '2026-03-03'
RUNOFF_DATE = '2026-05-26'
DISTRICT = 'HD-41'
CURRENT_YEAR = 2026


def age_bucket(by):
    if not by or by < 1900: return None
    age = CURRENT_YEAR - by
    if age < 18: return None
    if age <= 25: return '18-25'
    if age <= 35: return '26-35'
    if age <= 45: return '36-45'
    if age <= 55: return '46-55'
    if age <= 65: return '56-65'
    return '65+'


def main():
    print(f"Caching March 3 primary results for {DISTRICT}...")
    conn = sqlite3.connect(DB_PATH)

    # ── All March primary voters in HD-41 ──
    march_voters = conn.execute("""
        SELECT
            v.vuid, v.lat, v.lng, v.precinct, v.address, v.city, v.zip,
            v.firstname, v.lastname, v.birth_year, v.sex,
            ve.party_voted, ve.voting_method
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ?
        AND v.state_house_district = ?
        ORDER BY v.precinct, v.lastname
    """, (MARCH_DATE, DISTRICT)).fetchall()

    # ── Check which March voters have returned for the runoff ──
    runoff_vuids = set(r[0] for r in conn.execute("""
        SELECT DISTINCT v.vuid
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ? AND v.state_house_district = ?
    """, (RUNOFF_DATE, DISTRICT)).fetchall())

    # ── Build voter list with return status ──
    voters = []
    dem_voters = []
    rep_voters = []
    precinct_data = {}

    for row in march_voters:
        vuid, lat, lng, precinct, address, city, zip_code, fn, ln, by, sex, party, method = row
        returned = vuid in runoff_vuids
        age = age_bucket(by)

        voter = {
            'vuid': vuid,
            'lat': lat,
            'lng': lng,
            'precinct': precinct,
            'name': f"{fn or ''} {ln or ''}".strip(),
            'birth_year': by,
            'sex': sex,
            'party_voted': party,
            'voting_method': method,
            'returned_for_runoff': returned,
            'age_group': age,
        }
        voters.append(voter)

        if party == 'Democratic':
            dem_voters.append(voter)
        elif party == 'Republican':
            rep_voters.append(voter)

        # Precinct aggregation
        if precinct not in precinct_data:
            precinct_data[precinct] = {
                'precinct': precinct,
                'total': 0, 'dem': 0, 'rep': 0,
                'dem_returned': 0, 'rep_returned': 0,
                'dem_not_returned': 0, 'rep_not_returned': 0,
                'lat': 0, 'lng': 0, 'lat_sum': 0, 'lng_sum': 0, 'coord_count': 0,
                'dem_age': {}, 'rep_age': {},
                'dem_method': {}, 'rep_method': {},
            }
        p = precinct_data[precinct]
        p['total'] += 1
        if lat and lng:
            p['lat_sum'] += lat
            p['lng_sum'] += lng
            p['coord_count'] += 1

        if party == 'Democratic':
            p['dem'] += 1
            if returned: p['dem_returned'] += 1
            else: p['dem_not_returned'] += 1
            if age: p['dem_age'][age] = p['dem_age'].get(age, 0) + 1
            m = method or 'unknown'
            p['dem_method'][m] = p['dem_method'].get(m, 0) + 1
        elif party == 'Republican':
            p['rep'] += 1
            if returned: p['rep_returned'] += 1
            else: p['rep_not_returned'] += 1
            if age: p['rep_age'][age] = p['rep_age'].get(age, 0) + 1
            m = method or 'unknown'
            p['rep_method'][m] = p['rep_method'].get(m, 0) + 1

    # Finalize precinct centroids
    precincts = []
    for pct, p in sorted(precinct_data.items()):
        if p['coord_count'] > 0:
            p['lat'] = round(p['lat_sum'] / p['coord_count'], 4)
            p['lng'] = round(p['lng_sum'] / p['coord_count'], 4)
        dem_retention = round(p['dem_returned'] / p['dem'] * 100, 1) if p['dem'] > 0 else 0
        rep_retention = round(p['rep_returned'] / p['rep'] * 100, 1) if p['rep'] > 0 else 0
        dem_share = round(p['dem'] / p['total'] * 100, 1) if p['total'] > 0 else 0

        precincts.append({
            'precinct': pct,
            'lat': p['lat'],
            'lng': p['lng'],
            'total': p['total'],
            'dem': p['dem'],
            'rep': p['rep'],
            'dem_share': dem_share,
            'rep_share': round(100 - dem_share, 1),
            'dem_returned': p['dem_returned'],
            'dem_not_returned': p['dem_not_returned'],
            'dem_retention_pct': dem_retention,
            'rep_returned': p['rep_returned'],
            'rep_not_returned': p['rep_not_returned'],
            'rep_retention_pct': rep_retention,
            'dem_age': p['dem_age'],
            'rep_age': p['rep_age'],
            'dem_method': p['dem_method'],
            'rep_method': p['rep_method'],
        })

    # ── Summary stats ──
    total_march = len(voters)
    total_dem = len(dem_voters)
    total_rep = len(rep_voters)
    dem_returned_total = sum(1 for v in dem_voters if v['returned_for_runoff'])
    rep_returned_total = sum(1 for v in rep_voters if v['returned_for_runoff'])
    dem_not_returned_total = total_dem - dem_returned_total
    rep_not_returned_total = total_rep - rep_returned_total

    # ── Mobilization targets: March voters who haven't returned ──
    dem_targets = [v for v in dem_voters if not v['returned_for_runoff']]
    rep_targets = [v for v in rep_voters if not v['returned_for_runoff']]

    # Sort targets by precinct for walk-list style output
    dem_targets.sort(key=lambda v: (v['precinct'] or '', v['name']))
    rep_targets.sort(key=lambda v: (v['precinct'] or '', v['name']))

    # ── Age breakdown for each party ──
    dem_age_total = {}
    rep_age_total = {}
    for v in dem_voters:
        ag = v['age_group']
        if ag: dem_age_total[ag] = dem_age_total.get(ag, 0) + 1
    for v in rep_voters:
        ag = v['age_group']
        if ag: rep_age_total[ag] = rep_age_total.get(ag, 0) + 1

    conn.close()

    # ── Write cache ──
    result = {
        'election_date': MARCH_DATE,
        'election_name': 'HD-41 Primary Election (First Round)',
        'generated_at': datetime.now().isoformat(),
        'summary': {
            'total_voted': total_march,
            'dem_total': total_dem,
            'rep_total': total_rep,
            'dem_share': round(total_dem / total_march * 100, 1) if total_march else 0,
            'rep_share': round(total_rep / total_march * 100, 1) if total_march else 0,
            'dem_returned': dem_returned_total,
            'dem_not_returned': dem_not_returned_total,
            'dem_retention_pct': round(dem_returned_total / total_dem * 100, 1) if total_dem else 0,
            'rep_returned': rep_returned_total,
            'rep_not_returned': rep_not_returned_total,
            'rep_retention_pct': round(rep_returned_total / total_rep * 100, 1) if total_rep else 0,
            'dem_age': dem_age_total,
            'rep_age': rep_age_total,
        },
        'precincts': precincts,
        # Mobilization targets — voters who voted in March but NOT in the runoff
        'dem_mobilization_targets': [{
            'vuid': v['vuid'], 'name': v['name'], 'precinct': v['precinct'],
            'address': f"{v.get('lat','')},{v.get('lng','')}" if v.get('lat') else '',
            'age_group': v['age_group'], 'method': v['voting_method']
        } for v in dem_targets],
        'rep_mobilization_targets': [{
            'vuid': v['vuid'], 'name': v['name'], 'precinct': v['precinct'],
            'address': f"{v.get('lat','')},{v.get('lng','')}" if v.get('lat') else '',
            'age_group': v['age_group'], 'method': v['voting_method']
        } for v in rep_targets],
        # Precinct-level targets summary (for map overlay)
        'dem_target_precincts': sorted(
            [{'precinct': p['precinct'], 'targets': p['dem_not_returned'], 'total_march': p['dem'],
              'retention': p['dem_retention_pct'], 'lat': p['lat'], 'lng': p['lng']}
             for p in precincts if p['dem_not_returned'] > 0],
            key=lambda x: x['targets'], reverse=True
        ),
        'rep_target_precincts': sorted(
            [{'precinct': p['precinct'], 'targets': p['rep_not_returned'], 'total_march': p['rep'],
              'retention': p['rep_retention_pct'], 'lat': p['lat'], 'lng': p['lng']}
             for p in precincts if p['rep_not_returned'] > 0],
            key=lambda x: x['targets'], reverse=True
        ),
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(result, f, separators=(',', ':'))

    print(f"\n✓ March primary: {total_march} voters (D:{total_dem} R:{total_rep})")
    print(f"  Dem retention: {dem_returned_total}/{total_dem} = {round(dem_returned_total/total_dem*100,1) if total_dem else 0}%")
    print(f"  Rep retention: {rep_returned_total}/{total_rep} = {round(rep_returned_total/total_rep*100,1) if total_rep else 0}%")
    print(f"  Dem mobilization targets: {dem_not_returned_total}")
    print(f"  Rep mobilization targets: {rep_not_returned_total}")
    print(f"  File: {Path(CACHE_PATH).stat().st_size / 1024:.0f} KB")


if __name__ == '__main__':
    main()
