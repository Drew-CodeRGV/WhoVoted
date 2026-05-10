#!/usr/bin/env python3
"""Generate the Politiquera Gazette for HD-41 runoff election."""
import sqlite3, json
from pathlib import Path
from datetime import datetime

DB = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/hd41_gazette.json'
ELECTION_DATE = '2026-05-26'
DISTRICT = 'HD-41'
YEAR = 2026

# Candidates
DEM_CANDIDATES = 'Julio Salinas vs. Victor "Seby" Haddad'
REP_CANDIDATES = 'Sergio Sanchez vs. Gary Groves'
RETIRING_REP = 'Bobby Guerra (D)'

def main():
    conn = sqlite3.connect(DB)

    # Total voters in HD-41 who voted in the runoff
    total = conn.execute("""
        SELECT COUNT(DISTINCT v.vuid) FROM voters v
        INNER JOIN voter_elections ve ON v.vuid=ve.vuid AND ve.election_date=?
        WHERE v.state_house_district=? AND v.lat IS NOT NULL
    """, (ELECTION_DATE, DISTRICT)).fetchone()[0]

    # Total registered in HD-41
    registered = conn.execute("""
        SELECT COUNT(*) FROM voters
        WHERE state_house_district=? AND lat IS NOT NULL
    """, (DISTRICT,)).fetchone()[0]

    turnout = round(total / registered * 100, 2) if registered else 0

    # Party breakdown
    party_rows = conn.execute("""
        SELECT ve.party_voted, COUNT(DISTINCT ve.vuid) as cnt
        FROM voter_elections ve
        INNER JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ? AND v.state_house_district = ?
        GROUP BY ve.party_voted
    """, (ELECTION_DATE, DISTRICT)).fetchall()
    party_counts = {r[0]: r[1] for r in party_rows if r[0]}
    dem_count = party_counts.get('Democratic', 0)
    rep_count = party_counts.get('Republican', 0)

    # Voting method breakdown
    method_rows = conn.execute("""
        SELECT ve.voting_method, COUNT(DISTINCT ve.vuid) as cnt
        FROM voter_elections ve
        INNER JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ? AND v.state_house_district = ?
        GROUP BY ve.voting_method
    """, (ELECTION_DATE, DISTRICT)).fetchall()
    methods = {r[0]: r[1] for r in method_rows if r[0]}

    # Age breakdown
    ages = conn.execute("""
        SELECT
            CASE WHEN (2026-v.birth_year)<=25 THEN '18-25'
                 WHEN (2026-v.birth_year)<=35 THEN '26-35'
                 WHEN (2026-v.birth_year)<=65 THEN '36-65'
                 ELSE '65+' END as ag,
            SUM(CASE WHEN ve.vuid IS NOT NULL THEN 1 ELSE 0 END) as voted,
            COUNT(*) as reg
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid=ve.vuid AND ve.election_date=?
        WHERE v.state_house_district=? AND v.lat IS NOT NULL
        GROUP BY ag
    """, (ELECTION_DATE, DISTRICT)).fetchall()
    age_dict = {a: {'voted': v, 'reg': r, 'pct': round(v/r*100, 2) if r else 0} for a, v, r in ages}

    # Compare to March primary turnout
    march_total = conn.execute("""
        SELECT COUNT(DISTINCT v.vuid) FROM voters v
        INNER JOIN voter_elections ve ON v.vuid=ve.vuid AND ve.election_date='2026-03-03'
        WHERE v.state_house_district=?
    """, (DISTRICT,)).fetchone()[0]

    conn.close()

    # Build gazette
    headline = f"{total:,} Have Voted in HD-41 Runoff — {turnout}% Turnout"
    subhead = f"Dem: {DEM_CANDIDATES} | Rep: {REP_CANDIDATES}"

    # Bullets
    bullets = []
    bullets.append(f"📊 {total:,} of {registered:,} registered HD-41 voters have cast a ballot — {turnout}%")
    if dem_count and rep_count:
        ratio = round(dem_count / rep_count, 1) if rep_count > 0 else '∞'
        bullets.append(f"🔵 Democratic ballots: {dem_count:,} | 🔴 Republican ballots: {rep_count:,} (ratio: {ratio}:1)")
    if march_total:
        runoff_pct = round(total / march_total * 100, 1) if march_total else 0
        bullets.append(f"📉 Runoff turnout is {runoff_pct}% of the March primary ({march_total:,} voted then)")
    young = age_dict.get('18-25', {})
    old = age_dict.get('65+', {})
    if young.get('pct') and old.get('pct'):
        ratio = round(old['pct'] / young['pct']) if young['pct'] > 0 else '∞'
        bullets.append(f"👴 65+ voters turn out at {old['pct']}% — {ratio}x the rate of 18-25 year olds ({young['pct']}%)")

    # Stories
    stories = []

    stories.append({
        'title': 'The Race to Replace Bobby Guerra',
        'icon': '🏛️',
        'text': f"After {RETIRING_REP} announced his retirement, HD-41 drew contested primaries in both parties. "
                f"Neither side produced a majority winner on March 3, sending both races to a May 26 runoff. "
                f"Democrats choose between {DEM_CANDIDATES}. Republicans choose between {REP_CANDIDATES}. "
                f"So far, {total:,} voters have shown up — {turnout}% of the {registered:,} registered in the district."
    })

    if dem_count and rep_count:
        stories.append({
            'title': 'The Party Split',
            'icon': '🗳️',
            'text': f"{dem_count:,} voters pulled Democratic ballots. {rep_count:,} pulled Republican. "
                    f"That's a {round(dem_count/rep_count, 1) if rep_count else '∞'}:1 ratio — "
                    f"{'consistent with HD-41\'s historically Democratic lean.' if dem_count > rep_count else 'a shift toward Republican participation.'} "
                    f"In a runoff, the smaller electorate amplifies the impact of each vote."
        })

    if march_total and total:
        drop = march_total - total
        drop_pct = round(drop / march_total * 100, 1)
        stories.append({
            'title': 'Runoff Drop-Off',
            'icon': '📉',
            'text': f"The March primary drew {march_total:,} voters. The runoff has {total:,} so far — "
                    f"a {drop_pct}% drop-off ({drop:,} fewer voters). "
                    f"Runoff elections consistently favor older, more engaged voters. "
                    f"The candidate who can mobilize March voters who haven't returned has the edge."
        })

    young_data = age_dict.get('18-25', {})
    old_data = age_dict.get('65+', {})
    if young_data.get('pct') and old_data.get('pct') and young_data['pct'] > 0:
        age_ratio = round(old_data['pct'] / young_data['pct'])
        stories.append({
            'title': 'The Age Gap',
            'icon': '👴',
            'text': f"65+ voters turn out at {old_data['pct']}%. 18-25 year olds at {young_data['pct']}%. "
                    f"That's a {age_ratio}x gap. In a low-turnout runoff, seniors dominate the electorate. "
                    f"Any candidate targeting younger voters faces a structural disadvantage."
        })

    early = methods.get('early-voting', 0)
    eday = methods.get('election-day', 0)
    mailin = methods.get('mail-in', 0)
    if early or eday or mailin:
        stories.append({
            'title': 'How They Voted',
            'icon': '📬',
            'text': f"Early voting: {early:,}. Election day: {eday:,}. Mail-in: {mailin:,}. "
                    f"{'Early voting dominates — most runoff voters are planners, not procrastinators.' if early > eday else 'Election day turnout is strong — ground game matters.'}"
        })

    result = {
        'headline': headline,
        'subhead': subhead,
        'date': datetime.now().strftime('%B %d, %Y'),
        'election_name': 'HD-41 Runoff Election',
        'election_date': ELECTION_DATE,
        'total_voted': total,
        'registered': registered,
        'turnout_pct': turnout,
        'party_breakdown': {'Democratic': dem_count, 'Republican': rep_count},
        'method_breakdown': methods,
        'march_primary_total': march_total,
        'bullets': bullets,
        'stories': stories,
        'candidates': {
            'Democratic': DEM_CANDIDATES,
            'Republican': REP_CANDIDATES,
            'retiring': RETIRING_REP
        }
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(result, f, separators=(',', ':'))
    print(f"Gazette: {total:,} voters, {turnout}% turnout, D:{dem_count} R:{rep_count}")

if __name__ == '__main__':
    main()
