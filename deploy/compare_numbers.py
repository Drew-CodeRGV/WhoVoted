#!/usr/bin/env python3
"""Compare old vs new numbers and break down Saturday vs weekday voting."""
import sqlite3, json
from datetime import datetime, timedelta

DB = '/opt/whovoted/data/whovoted.db'
ZIPS = ('78501','78502','78503','78504','78505')
ELECTION = '2026-05-10'

conn = sqlite3.connect(DB)
ph = ','.join('?' * len(ZIPS))

# Total McAllen voters
total = conn.execute(f"""
    SELECT COUNT(DISTINCT v.vuid)
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
    WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
""", (ELECTION,) + ZIPS).fetchone()[0]
print(f"Total McAllen voters: {total:,}")

# By voting method
methods = conn.execute(f"""
    SELECT ve.voting_method, COUNT(DISTINCT v.vuid)
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
    WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
    GROUP BY ve.voting_method
""", (ELECTION,) + ZIPS).fetchall()
print("\nBy method:")
for m, c in methods:
    print(f"  {m}: {c:,}")

# Daily breakdown with day of week
print("\nDaily breakdown:")
daily = conn.execute(f"""
    SELECT DATE(ve.created_at) as d, COUNT(*) as c, ve.voting_method
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
    WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL
    GROUP BY d, ve.voting_method
    ORDER BY d
""", (ELECTION,) + ZIPS).fetchall()

day_totals = {}
for d, c, m in daily:
    if d not in day_totals:
        day_totals[d] = {'total': 0, 'methods': {}}
    day_totals[d]['total'] += c
    day_totals[d]['methods'][m] = c

cum = 0
sat_total = 0; weekday_total = 0; sat_days = 0; weekday_days = 0
for d in sorted(day_totals.keys()):
    dt = day_totals[d]
    cum += dt['total']
    # Shift back 1 day (roster posted day after voting)
    try:
        actual = datetime.strptime(d, '%Y-%m-%d') - timedelta(days=1)
        dow = actual.strftime('%a')
        actual_str = actual.strftime('%Y-%m-%d')
    except:
        dow = '?'
        actual_str = d
    
    is_sat = dow == 'Sat'
    if is_sat:
        sat_total += dt['total']
        sat_days += 1
    else:
        weekday_total += dt['total']
        weekday_days += 1
    
    methods_str = ', '.join(f"{m}:{c}" for m, c in dt['methods'].items())
    print(f"  {actual_str} ({dow}): +{dt['total']:,} = {cum:,} total  [{methods_str}]")

print(f"\nSaturday voting: {sat_total:,} votes over {sat_days} day(s) = {sat_total/sat_days:.0f}/day avg" if sat_days else "")
print(f"Weekday voting: {weekday_total:,} votes over {weekday_days} day(s) = {weekday_total/weekday_days:.0f}/day avg" if weekday_days else "")
if sat_days and weekday_days:
    ratio = (sat_total/sat_days) / (weekday_total/weekday_days)
    print(f"Saturday avg is {ratio:.1f}x the weekday avg")

# Age breakdown of new voters (last 2 days vs earlier)
print("\n=== NEW vs EARLIER VOTERS ===")
all_dates = sorted(day_totals.keys())
if len(all_dates) >= 3:
    cutoff = all_dates[-2]  # last 2 roster dates
    print(f"Recent (since {cutoff}): vs Earlier")
    
    recent = conn.execute(f"""
        SELECT
            CASE WHEN (2026 - v.birth_year) <= 35 THEN 'Young (18-35)'
                 WHEN (2026 - v.birth_year) <= 55 THEN 'Middle (36-55)'
                 ELSE 'Senior (56+)' END as ag,
            COUNT(*)
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL AND ve.created_at >= ?
        GROUP BY ag
    """, (ELECTION,) + ZIPS + (cutoff,)).fetchall()
    
    earlier = conn.execute(f"""
        SELECT
            CASE WHEN (2026 - v.birth_year) <= 35 THEN 'Young (18-35)'
                 WHEN (2026 - v.birth_year) <= 55 THEN 'Middle (36-55)'
                 ELSE 'Senior (56+)' END as ag,
            COUNT(*)
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid AND ve.election_date = ?
        WHERE v.zip IN ({ph}) AND v.lat IS NOT NULL AND ve.created_at < ?
        GROUP BY ag
    """, (ELECTION,) + ZIPS + (cutoff,)).fetchall()
    
    print("  Recent:")
    for ag, c in recent:
        print(f"    {ag}: {c}")
    print("  Earlier:")
    for ag, c in earlier:
        print(f"    {ag}: {c}")

# Registered total
reg = conn.execute(f"SELECT COUNT(*) FROM voters WHERE zip IN ({ph}) AND lat IS NOT NULL", ZIPS).fetchone()[0]
print(f"\nRegistered: {reg:,}")
print(f"Turnout: {total/reg*100:.2f}%")

conn.close()
