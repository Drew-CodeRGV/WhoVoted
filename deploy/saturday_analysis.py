#!/usr/bin/env python3
"""Detailed Saturday vs weekday analysis."""
import sqlite3
DB = '/opt/whovoted/data/whovoted.db'
ZIPS = ('78501','78502','78503','78504','78505')
ELECTION = '2026-05-10'

conn = sqlite3.connect(DB)
ph = ','.join('?' * len(ZIPS))

# The roster dates map to actual voting dates (shift back 1 day):
# created_at 2026-04-22 = voted 2026-04-21 (Mon, Day 1)
# created_at 2026-04-23 = voted 2026-04-22 (Tue, Day 2) 
# created_at 2026-04-24 = voted 2026-04-23 (Wed, Day 3)
# created_at 2026-04-25 = voted 2026-04-24 (Thu, Day 4)
# created_at 2026-04-27 = voted 2026-04-26 (Sat, Day 5)

# Saturday voters (created_at on Sunday = voted Saturday)
# Let's identify by looking at the actual created_at dates
print("=== VOTES BY ROSTER DATE (actual voting day = date - 1) ===")
rows = conn.execute(f"""
    SELECT DATE(ve.created_at) as roster_date, 
           ve.voting_method,
           COUNT(*) as cnt
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
    WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
    GROUP BY roster_date, ve.voting_method
    ORDER BY roster_date
""", (ELECTION,) + ZIPS).fetchall()

from datetime import datetime, timedelta
day_data = {}
for rd, method, cnt in rows:
    actual = (datetime.strptime(rd, '%Y-%m-%d') - timedelta(days=1)).strftime('%Y-%m-%d')
    dow = (datetime.strptime(rd, '%Y-%m-%d') - timedelta(days=1)).strftime('%A')
    if actual not in day_data:
        day_data[actual] = {'dow': dow, 'total': 0, 'early': 0, 'mailin': 0}
    day_data[actual]['total'] += cnt
    if 'early' in method: day_data[actual]['early'] += cnt
    elif 'mail' in method: day_data[actual]['mailin'] += cnt

cum = 0
for d in sorted(day_data.keys()):
    dd = day_data[d]
    cum += dd['total']
    print(f"  {d} ({dd['dow'][:3]}): +{dd['total']:>4} (EV:{dd['early']:>4}, Mail:{dd['mailin']:>3}) = {cum:,} total")

# Saturday specifically
sat_dates = [d for d in day_data if day_data[d]['dow'] == 'Saturday']
weekday_dates = [d for d in day_data if day_data[d]['dow'] not in ('Saturday', 'Sunday')]

sat_total = sum(day_data[d]['total'] for d in sat_dates)
wk_total = sum(day_data[d]['total'] for d in weekday_dates)
sat_avg = sat_total / len(sat_dates) if sat_dates else 0
wk_avg = wk_total / len(weekday_dates) if weekday_dates else 0

print(f"\nSaturday: {sat_total:,} votes ({len(sat_dates)} day) = {sat_avg:.0f}/day")
print(f"Weekdays: {wk_total:,} votes ({len(weekday_dates)} days) = {wk_avg:.0f}/day")
if wk_avg > 0:
    print(f"Saturday was {'higher' if sat_avg > wk_avg else 'lower'}: {sat_avg/wk_avg:.2f}x weekday average")

# Age breakdown: Saturday voters vs weekday voters
print("\n=== SATURDAY vs WEEKDAY AGE PROFILE ===")
# Saturday = roster date is Sunday (2026-04-27)
sat_roster = '2026-04-27'
sat_ages = conn.execute(f"""
    SELECT
        CASE WHEN (2026 - v.birth_year) <= 25 THEN '18-25'
             WHEN (2026 - v.birth_year) <= 35 THEN '26-35'
             WHEN (2026 - v.birth_year) <= 45 THEN '36-45'
             WHEN (2026 - v.birth_year) <= 55 THEN '46-55'
             WHEN (2026 - v.birth_year) <= 65 THEN '56-65'
             ELSE '65+' END as ag,
        COUNT(*) as c
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
    WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL AND DATE(ve.created_at) = ?
    GROUP BY ag ORDER BY ag
""", (ELECTION,) + ZIPS + (sat_roster,)).fetchall()

wk_ages = conn.execute(f"""
    SELECT
        CASE WHEN (2026 - v.birth_year) <= 25 THEN '18-25'
             WHEN (2026 - v.birth_year) <= 35 THEN '26-35'
             WHEN (2026 - v.birth_year) <= 45 THEN '36-45'
             WHEN (2026 - v.birth_year) <= 55 THEN '46-55'
             WHEN (2026 - v.birth_year) <= 65 THEN '56-65'
             ELSE '65+' END as ag,
        COUNT(*) as c
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
    WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL AND DATE(ve.created_at) != ?
    GROUP BY ag ORDER BY ag
""", (ELECTION,) + ZIPS + (sat_roster,)).fetchall()

sat_dict = dict(sat_ages)
wk_dict = dict(wk_ages)
sat_t = sum(sat_dict.values())
wk_t = sum(wk_dict.values())

print(f"{'Age':<8} {'Sat':>6} {'Sat%':>6} {'Wkday':>6} {'Wk%':>6} {'Shift':>8}")
for ag in ['18-25','26-35','36-45','46-55','56-65','65+']:
    s = sat_dict.get(ag, 0)
    w = wk_dict.get(ag, 0)
    sp = s/sat_t*100 if sat_t else 0
    wp = w/wk_t*100 if wk_t else 0
    shift = sp - wp
    arrow = '↑' if shift > 0.5 else '↓' if shift < -0.5 else '→'
    print(f"{ag:<8} {s:>6} {sp:>5.1f}% {w:>6} {wp:>5.1f}% {arrow}{abs(shift):>5.1f}pp")

# Gender on Saturday vs weekday
print("\n=== SATURDAY vs WEEKDAY GENDER ===")
for label, date_filter in [('Saturday', f"DATE(ve.created_at) = '{sat_roster}'"), ('Weekdays', f"DATE(ve.created_at) != '{sat_roster}'")]:
    g = conn.execute(f"""
        SELECT v.sex, COUNT(*)
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL AND {date_filter}
        GROUP BY v.sex
    """, (ELECTION,) + ZIPS).fetchall()
    gd = dict(g)
    t = sum(gd.values())
    f_pct = gd.get('F',0)/t*100 if t else 0
    m_pct = gd.get('M',0)/t*100 if t else 0
    print(f"  {label}: Women {gd.get('F',0)} ({f_pct:.1f}%), Men {gd.get('M',0)} ({m_pct:.1f}%)")

conn.close()
