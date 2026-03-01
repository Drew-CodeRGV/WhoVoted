#!/usr/bin/env python3
"""Deep analysis of 2026 early vote turnout vs 2022 and 2024 primaries."""
import sys, os
sys.path.insert(0, '/opt/whovoted/backend')
os.chdir('/opt/whovoted/backend')
import database as db
db.init_db()
conn = db.get_connection()

print("=" * 70)
print("HIDALGO COUNTY 2026 PRIMARY EARLY VOTE ANALYSIS")
print("Data as of: Feb 24, 2026 (early voting ongoing, election day Mar 3)")
print("=" * 70)

# === OVERALL TURNOUT COMPARISON ===
print("\n1. OVERALL EARLY VOTE TURNOUT COMPARISON")
print("-" * 50)

ev_2022 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND voting_method='early-voting'").fetchone()[0]
ed_2022 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND voting_method='election-day'").fetchone()[0]
total_2022 = ev_2022 + ed_2022

ev_2024 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND voting_method='early-voting'").fetchone()[0]
ed_2024 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND voting_method='election-day'").fetchone()[0]
total_2024 = ev_2024 + ed_2024

ev_2026 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03'").fetchone()[0]

print(f"  2022 Primary (final):  {ev_2022:,} early + {ed_2022:,} election day = {total_2022:,} total")
print(f"  2024 Primary (final):  {ev_2024:,} early + {ed_2024:,} election day = {total_2024:,} total")
print(f"  2026 Primary (EV so far): {ev_2026:,} early votes")
print(f"")
print(f"  2026 EV vs 2022 EV: {ev_2026/ev_2022*100:.1f}% ({ev_2026-ev_2022:+,})")
print(f"  2026 EV vs 2024 EV: {ev_2024 and f'{ev_2026/ev_2024*100:.1f}%' or 'N/A'} ({ev_2026-ev_2024:+,})")
print(f"  2026 EV vs 2022 TOTAL: {ev_2026/total_2022*100:.1f}% of 2022 final total already cast")
print(f"  2026 EV vs 2024 TOTAL: {ev_2026/total_2024*100:.1f}% of 2024 final total already cast")

# === PARTY BREAKDOWN ===
print("\n2. PARTY BREAKDOWN")
print("-" * 50)

for year, edate in [('2022', '2022-03-01'), ('2024', '2024-03-05'), ('2026', '2026-03-03')]:
    dem = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date=? AND party_voted='Democratic'", (edate,)).fetchone()[0]
    rep = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date=? AND party_voted='Republican'", (edate,)).fetchone()[0]
    total = dem + rep
    dem_pct = dem/total*100 if total else 0
    rep_pct = rep/total*100 if total else 0
    suffix = " (EV only so far)" if year == '2026' else " (final)"
    print(f"  {year}{suffix}:")
    print(f"    DEM: {dem:>7,} ({dem_pct:.1f}%)   REP: {rep:>7,} ({rep_pct:.1f}%)   Total: {total:,}")

# Party shift over time
dem_2022 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND party_voted='Democratic'").fetchone()[0]
rep_2022 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND party_voted='Republican'").fetchone()[0]
dem_2026 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Democratic'").fetchone()[0]
rep_2026 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Republican'").fetchone()[0]
dem_2024_total = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND party_voted='Democratic'").fetchone()[0]
rep_2024_total = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND party_voted='Republican'").fetchone()[0]

print(f"\n  DEM share trend: {dem_2022/(dem_2022+rep_2022)*100:.1f}% (2022) → {dem_2024_total/(dem_2024_total+rep_2024_total)*100:.1f}% (2024) → {dem_2026/(dem_2026+rep_2026)*100:.1f}% (2026 EV)")
print(f"  REP share trend: {rep_2022/(dem_2022+rep_2022)*100:.1f}% (2022) → {rep_2024_total/(dem_2024_total+rep_2024_total)*100:.1f}% (2024) → {rep_2026/(dem_2026+rep_2026)*100:.1f}% (2026 EV)")

# === FLIPPED VOTERS ===
print("\n3. FLIPPED VOTERS (party switch from immediately preceding election)")
print("-" * 50)

for year, edate in [('2024', '2024-03-05'), ('2026', '2026-03-03')]:
    flips = conn.execute("""
        SELECT ve_current.party_voted as to_party, ve_prev.party_voted as from_party, COUNT(*) as cnt
        FROM voter_elections ve_current
        JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
        WHERE ve_current.election_date = ?
            AND ve_prev.election_date = (
                SELECT MAX(ve2.election_date) FROM voter_elections ve2
                WHERE ve2.vuid = ve_current.vuid
                    AND ve2.election_date < ve_current.election_date
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
            )
            AND ve_current.party_voted != ve_prev.party_voted
            AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
        GROUP BY ve_current.party_voted, ve_prev.party_voted
        ORDER BY cnt DESC
    """, (edate,)).fetchall()
    
    total_flips = sum(r[2] for r in flips)
    total_voters = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date=?", (edate,)).fetchone()[0]
    print(f"  {year} ({edate}): {total_flips:,} flips ({total_flips/total_voters*100:.1f}% of voters)")
    for r in flips:
        print(f"    {r[1]} → {r[0]}: {r[2]:,}")

# === NEW VOTERS ===
print("\n4. NEW VOTERS (first-time primary voters)")
print("-" * 50)

for year, edate in [('2022', '2022-03-01'), ('2024', '2024-03-05'), ('2026', '2026-03-03')]:
    new_total = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        WHERE ve.election_date = ?
          AND NOT EXISTS (
              SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
          )
    """, (edate, edate)).fetchone()[0]
    
    new_dem = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        WHERE ve.election_date = ? AND ve.party_voted = 'Democratic'
          AND NOT EXISTS (
              SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
          )
    """, (edate, edate)).fetchone()[0]
    
    new_rep = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        WHERE ve.election_date = ? AND ve.party_voted = 'Republican'
          AND NOT EXISTS (
              SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
          )
    """, (edate, edate)).fetchone()[0]
    
    total = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date=?", (edate,)).fetchone()[0]
    suffix = " (EV only)" if year == '2026' else " (final)"
    print(f"  {year}{suffix}: {new_total:,} new voters ({new_total/total*100:.1f}% of turnout)")
    print(f"    New DEM: {new_dem:,}   New REP: {new_rep:,}")

# === RETURNING VOTERS ===
print("\n5. RETURNING vs LAPSED VOTERS")
print("-" * 50)

# Voters in 2026 who also voted in 2024
both_24_26 = conn.execute("""
    SELECT COUNT(DISTINCT ve26.vuid) FROM voter_elections ve26
    JOIN voter_elections ve24 ON ve26.vuid = ve24.vuid
    WHERE ve26.election_date = '2026-03-03' AND ve24.election_date = '2024-03-05'
""").fetchone()[0]

# Voters in 2026 who voted in 2022 but NOT 2024
from_22_skip_24 = conn.execute("""
    SELECT COUNT(DISTINCT ve26.vuid) FROM voter_elections ve26
    JOIN voter_elections ve22 ON ve26.vuid = ve22.vuid
    WHERE ve26.election_date = '2026-03-03' AND ve22.election_date = '2022-03-01'
      AND NOT EXISTS (
          SELECT 1 FROM voter_elections ve24
          WHERE ve24.vuid = ve26.vuid AND ve24.election_date = '2024-03-05'
      )
""").fetchone()[0]

# Voters in 2024 who haven't voted in 2026 yet
voted_24_not_26 = conn.execute("""
    SELECT COUNT(DISTINCT ve24.vuid) FROM voter_elections ve24
    WHERE ve24.election_date = '2024-03-05'
      AND NOT EXISTS (
          SELECT 1 FROM voter_elections ve26
          WHERE ve26.vuid = ve24.vuid AND ve26.election_date = '2026-03-03'
      )
""").fetchone()[0]

print(f"  2026 voters who also voted in 2024: {both_24_26:,}")
print(f"  2026 voters who voted in 2022 but skipped 2024: {from_22_skip_24:,}")
print(f"  2024 voters who haven't voted in 2026 yet: {voted_24_not_26:,}")

# === CROSS-PARTY VOTERS (voted different party in different years) ===
print("\n6. CROSS-PARTY VOTING PATTERNS (2022 → 2024 → 2026)")
print("-" * 50)

patterns = conn.execute("""
    SELECT 
        ve22.party_voted as p22,
        ve24.party_voted as p24,
        ve26.party_voted as p26,
        COUNT(*) as cnt
    FROM voter_elections ve26
    JOIN voter_elections ve24 ON ve26.vuid = ve24.vuid
    JOIN voter_elections ve22 ON ve26.vuid = ve22.vuid
    WHERE ve26.election_date = '2026-03-03'
      AND ve24.election_date = '2024-03-05'
      AND ve22.election_date = '2022-03-01'
      AND ve22.party_voted != '' AND ve24.party_voted != '' AND ve26.party_voted != ''
    GROUP BY ve22.party_voted, ve24.party_voted, ve26.party_voted
    ORDER BY cnt DESC
""").fetchall()

total_3way = sum(r[3] for r in patterns)
print(f"  Voters with all 3 elections: {total_3way:,}")
for r in patterns:
    pct = r[3]/total_3way*100
    label = f"{r[0][0]}→{r[1][0]}→{r[2][0]}"
    bar = "█" * int(pct / 2)
    print(f"    {label}: {r[3]:>6,} ({pct:5.1f}%) {bar}")

# === TOP PRECINCTS BY FLIPS ===
print("\n7. TOP 10 PRECINCTS BY FLIP COUNT (2026)")
print("-" * 50)

top_precincts = conn.execute("""
    SELECT ve_current.precinct, COUNT(*) as flip_count,
           SUM(CASE WHEN ve_current.party_voted = 'Democratic' THEN 1 ELSE 0 END) as to_dem,
           SUM(CASE WHEN ve_current.party_voted = 'Republican' THEN 1 ELSE 0 END) as to_rep
    FROM voter_elections ve_current
    JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
    WHERE ve_current.election_date = '2026-03-03'
        AND ve_prev.election_date = (
            SELECT MAX(ve2.election_date) FROM voter_elections ve2
            WHERE ve2.vuid = ve_current.vuid
                AND ve2.election_date < '2026-03-03'
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
        )
        AND ve_current.party_voted != ve_prev.party_voted
        AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
        AND ve_current.precinct != ''
    GROUP BY ve_current.precinct
    ORDER BY flip_count DESC
    LIMIT 10
""").fetchall()

for r in top_precincts:
    print(f"  Precinct {r[0]}: {r[1]} flips (→DEM: {r[2]}, →REP: {r[3]})")

print("\n" + "=" * 70)
