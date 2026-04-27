#!/usr/bin/env python3
"""Generate the Politiquera Gazette data - newspaper-style summary of bond election."""
import sqlite3, json
from pathlib import Path
from datetime import datetime, timedelta

DB = '/opt/whovoted/data/whovoted.db'
CACHE_PATH = '/opt/whovoted/public/cache/misdbond2026_gazette.json'
ELECTION = '2026-05-10'
ZIPS = ('78501','78502','78503','78504','78505')
YEAR = 2026

def main():
    conn = sqlite3.connect(DB)
    ph = ','.join('?' * len(ZIPS))

    # Total voters
    total = conn.execute(f"""
        SELECT COUNT(DISTINCT v.vuid) FROM voters v
        INNER JOIN voter_elections ve ON v.vuid=ve.vuid AND ve.election_date=?
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
    """, (ELECTION,)+ZIPS).fetchone()[0]

    registered = conn.execute(f"SELECT COUNT(*) FROM voters WHERE zip IN ({ph}) AND lat IS NOT NULL", ZIPS).fetchone()[0]
    turnout = round(total/registered*100, 2) if registered else 0

    # Daily breakdown
    daily_raw = conn.execute(f"""
        SELECT DATE(ve.created_at) as d, COUNT(*) as c
        FROM voters v INNER JOIN voter_elections ve ON v.vuid=ve.vuid AND ve.election_date=?
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
        GROUP BY d ORDER BY d
    """, (ELECTION,)+ZIPS).fetchall()

    daily = []
    prev = 0
    for d, c in daily_raw:
        try:
            actual = (datetime.strptime(d, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
            dow = (datetime.strptime(d, '%Y-%m-%d') - timedelta(days=1)).strftime('%a')
        except:
            actual = d; dow = '?'
        prev += c
        daily.append({'date': actual, 'dow': dow, 'new': c, 'total': prev})

    today_new = daily[-1]['new'] if daily else 0
    yesterday_new = daily[-2]['new'] if len(daily) >= 2 else 0
    change = today_new - yesterday_new
    change_pct = round(change/yesterday_new*100, 1) if yesterday_new else 0

    # District highlights (top + bottom)
    districts = json.load(open('/opt/whovoted/public/cache/misdbond2026_reportcard.json'))
    d_sorted = sorted(districts['districts'], key=lambda x: x['turnout_pct'], reverse=True)
    top_dist = d_sorted[0] if d_sorted else None
    bot_dist = d_sorted[-1] if d_sorted else None

    # School highlights
    ms = json.load(open('/opt/whovoted/public/cache/misdbond2026_campus_reportcard.json'))
    hs = json.load(open('/opt/whovoted/public/cache/misdbond2026_hs_reportcard.json'))
    elem = json.load(open('/opt/whovoted/public/cache/misdbond2026_elem_reportcard.json'))
    all_schools = ms['campuses'] + hs['campuses'] + elem['campuses']
    all_schools = [s for s in all_schools if s['registered'] > 0]
    s_sorted = sorted(all_schools, key=lambda x: x['turnout_pct'], reverse=True)
    top_school = s_sorted[0] if s_sorted else None
    bot_school = s_sorted[-1] if len(s_sorted) > 1 else None

    # Staff
    staff = json.load(open('/opt/whovoted/public/cache/misdbond2026_staff.json'))

    # Age extremes
    ages = conn.execute(f"""
        SELECT
            CASE WHEN (2026-v.birth_year)<=25 THEN '18-25'
                 WHEN (2026-v.birth_year)<=35 THEN '26-35'
                 WHEN (2026-v.birth_year)<=65 THEN '36-65'
                 ELSE '65+' END as ag,
            SUM(CASE WHEN ve.vuid IS NOT NULL THEN 1 ELSE 0 END) as voted,
            COUNT(*) as reg
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid=ve.vuid AND ve.election_date=?
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
        GROUP BY ag
    """, (ELECTION,)+ZIPS).fetchall()
    age_dict = {a: {'voted': v, 'reg': r, 'pct': round(v/r*100,2) if r else 0} for a, v, r in ages}

    # Build gazette
    headline = f"{total:,} Have Voted — {turnout}% Turnout"
    if change > 0:
        subhead = f"+{today_new:,} new votes today ({'+' if change>0 else ''}{change_pct}% vs yesterday)"
    elif today_new > 0:
        subhead = f"+{today_new:,} new votes today"
    else:
        subhead = "Waiting for new data..."

    # Bullet points
    bullets = []
    bullets.append(f"📊 {total:,} of {registered:,} registered McAllen voters have cast a ballot — that's {turnout}%")
    if top_dist and bot_dist:
        bullets.append(f"🏛️ {top_dist['name']} leads at {top_dist['turnout_pct']}% ({top_dist['grade']}). {bot_dist['name']} trails at {bot_dist['turnout_pct']}% ({bot_dist['grade']}) — a {round(top_dist['turnout_pct']/bot_dist['turnout_pct'],1) if bot_dist['turnout_pct']>0 else '∞'}x gap")
    if top_school and bot_school:
        bullets.append(f"🏫 {top_school['name']} is the top campus at {top_school['turnout_pct']}% ({top_school['grade']}). {bot_school['name']} is last at {bot_school['turnout_pct']}% ({bot_school['grade']})")
    young = age_dict.get('18-25', {})
    old = age_dict.get('65+', {})
    if young.get('pct') and old.get('pct'):
        ratio = round(old['pct']/young['pct'], 0) if young['pct'] > 0 else '∞'
        bullets.append(f"👴 65+ voters turn out at {old['pct']}% — {ratio}x the rate of 18-25 year olds ({young['pct']}%)")
    bullets.append(f"👩‍🏫 {staff['voted']} of {staff['matched_to_voters']} MISD staff in voter rolls have voted ({staff['turnout_pct']}%). Teachers lead at {next((r['turnout_pct'] for r in staff.get('roles',[]) if r['role']=='Instructional'), '?')}%")

    # District column
    dist_col = []
    for d in d_sorted:
        dist_col.append({'name': d['name'], 'rep': d.get('rep',''), 'voted': d['voted'],
                         'registered': d['registered'], 'pct': d['turnout_pct'], 'grade': d['grade']})

    # School column (top 5 + bottom 5)
    school_col_top = [{'name':s['name'],'voted':s['voted'],'registered':s['registered'],
                       'pct':s['turnout_pct'],'grade':s['grade']} for s in s_sorted[:5]]
    school_col_bot = [{'name':s['name'],'voted':s['voted'],'registered':s['registered'],
                       'pct':s['turnout_pct'],'grade':s['grade']} for s in s_sorted[-5:]]

    # Staff column
    staff_col = [{'role':r['role'],'icon':r['icon'],'voted':r['voted'],'matched':r['matched'],
                  'total':r['total'],'pct':r['turnout_pct']} for r in staff.get('roles',[])]

    # F-grade schools
    f_schools = [s for s in all_schools if s['grade'] == 'F' and s['registered'] > 0]
    f_total_reg = sum(s['registered'] for s in f_schools)
    f_total_voted = sum(s['voted'] for s in f_schools)
    f_names = ', '.join(s['name'] for s in f_schools[:4])

    # Stories
    stories = []

    # Story 1: The Overview
    not_voted_pct = round(100 - turnout, 1)
    stories.append({
        'title': 'A City Deciding Its Future in Slow Motion',
        'icon': '🏙️',
        'text': f"McAllen ISD put a $335 million bond on the ballot to modernize every campus in the district. "
                f"So far, {total:,} of {registered:,} registered voters have shown up — {turnout}%. "
                f"That means {not_voted_pct}% of McAllen hasn't weighed in on a decision that affects 20,058 students, "
                f"68% of whom are economically disadvantaged. The district earned a TEA 'A' rating and a 98% graduation rate "
                f"despite aging facilities. The buildings need the work. The question is whether enough people care to say yes or no."
    })

    # Story 2: Two McAllens
    if top_school and bot_school and bot_school['turnout_pct'] > 0:
        gap = round(top_school['turnout_pct'] / bot_school['turnout_pct'], 0)
        stories.append({
            'title': 'Two McAllens: The North-South Divide',
            'icon': '🗺️',
            'text': f"The data draws a line across the city. {top_school['name']} leads all campuses at "
                    f"{top_school['turnout_pct']}% ({top_school['grade']}), in north McAllen's established neighborhoods. "
                    f"Meanwhile {bot_school['name']} sits at {bot_school['turnout_pct']}% ({bot_school['grade']}) in south McAllen. "
                    f"That's a {gap:.0f}x gap. "
                    f"The F-grade zones ({f_names}) contain {f_total_reg:,} registered voters — {f_total_voted} have voted ({round(f_total_voted/f_total_reg*100,2) if f_total_reg else 0}%). "
                    f"The campuses that need modernization most are surrounded by the voters least likely to show up."
        })

    # Story 3: The Age Cliff
    young_data = age_dict.get('18-25', {})
    old_data = age_dict.get('65+', {})
    if young_data.get('pct') and old_data.get('pct') and young_data['pct'] > 0:
        age_ratio = round(old_data['pct'] / young_data['pct'])
        stories.append({
            'title': 'The Age Cliff: Grandparents Decide',
            'icon': '👴',
            'text': f"65+ voters turn out at {old_data['pct']}%. 18-25 year olds at {young_data['pct']}%. "
                    f"That's a {age_ratio}x gap. The people whose kids graduated decades ago are deciding the future "
                    f"of the kids in school right now. There are an estimated 77,744 school-age children in McAllen "
                    f"and only {total:,} adults have voted — roughly 1 voter for every {round(77744/total) if total else '?'} students."
        })

    # Story 4: District 4
    if bot_dist:
        stories.append({
            'title': f"District 4: The Silent Majority",
            'icon': '🏚️',
            'text': f"{bot_dist['name']} ({bot_dist.get('rep','')}) has {bot_dist['registered']:,} registered voters "
                    f"and {bot_dist['voted']} have shown up — {bot_dist['turnout_pct']}%, a {bot_dist['grade']} grade. "
                    f"This is south McAllen — younger, more working-class, more school-age children per household. "
                    f"The bond's classroom additions would have the most impact here. "
                    f"Meanwhile {top_dist['name']} ({top_dist.get('rep','')}) leads at {top_dist['turnout_pct']}% — "
                    f"a {round(top_dist['turnout_pct']/bot_dist['turnout_pct'],1) if bot_dist['turnout_pct'] > 0 else '?'}x difference."
        })

    # Story 5: The Teachers Get It
    instr = next((r for r in staff.get('roles', []) if r['role'] == 'Instructional'), None)
    fac = next((r for r in staff.get('roles', []) if r['role'] == 'Facilities & Operations'), None)
    if instr and fac:
        stories.append({
            'title': 'The Teachers Get It',
            'icon': '👩‍🏫',
            'text': f"Of {staff['total_staff']:,} MISD staff, {staff['matched_to_voters']} were found in McAllen voter rolls. "
                    f"{staff['voted']} have voted ({staff['turnout_pct']}%). Teachers and instructional staff lead at "
                    f"{instr['turnout_pct']}% — {round(instr['turnout_pct']/fac['turnout_pct'],1) if fac['turnout_pct'] > 0 else '?'}x "
                    f"the rate of facilities staff ({fac['turnout_pct']}%). "
                    f"The people closest to the classroom care the most about what happens to it."
        })

    result = {
        'headline': headline,
        'subhead': subhead,
        'date': datetime.now().strftime('%B %d, %Y'),
        'total_voted': total,
        'registered': registered,
        'turnout_pct': turnout,
        'daily': daily,
        'today_new': today_new,
        'yesterday_new': yesterday_new,
        'change': change,
        'change_pct': change_pct,
        'bullets': bullets,
        'districts': dist_col,
        'schools_top': school_col_top,
        'schools_bottom': school_col_bot,
        'staff': staff_col,
        'staff_summary': {'voted': staff['voted'], 'matched': staff['matched_to_voters'],
                          'total': staff['total_staff'], 'pct': staff['turnout_pct']},
        'overall_grade': districts['summary']['overall_grade'],
        'stories': stories
    }

    Path(CACHE_PATH).parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'w') as f:
        json.dump(result, f, separators=(',',':'))
    print(f"Gazette: {total:,} voters, {turnout}% turnout, +{today_new} today")

if __name__ == '__main__':
    main()
