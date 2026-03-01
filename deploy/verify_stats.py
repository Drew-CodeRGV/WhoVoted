#!/usr/bin/env python3
"""Verify database stats vs what the API returns."""
import sqlite3
import json
import urllib.request

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=" * 90)
print("ELECTIONS IN DB (voter_elections table)")
print("=" * 90)
rows = conn.execute('''
    SELECT v.county, ve.election_date, ve.election_type, ve.voting_method, ve.party_voted,
           COUNT(DISTINCT ve.vuid) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    GROUP BY v.county, ve.election_date, ve.election_type, ve.voting_method, ve.party_voted
    ORDER BY ve.election_date DESC, v.county, ve.party_voted
''').fetchall()
for r in rows:
    print(f"  {r['county']:10s} {r['election_date']} {r['election_type']:10s} "
          f"{r['voting_method']:15s} {r['party_voted']:15s} count={r['cnt']}")

print()
print("=" * 90)
print("TOTALS PER ELECTION (grouped by county/date/method)")
print("=" * 90)
rows = conn.execute('''
    SELECT v.county, ve.election_date, ve.election_type, ve.voting_method,
           COUNT(DISTINCT ve.vuid) as total,
           COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
           COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep,
           COUNT(DISTINCT CASE WHEN v.geocoded = 1 THEN ve.vuid END) as geocoded
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    GROUP BY v.county, ve.election_date, ve.election_type, ve.voting_method
    ORDER BY ve.election_date DESC, v.county
''').fetchall()
for r in rows:
    ungeo = r['total'] - r['geocoded']
    pct = (r['geocoded'] / r['total'] * 100) if r['total'] > 0 else 0
    print(f"  {r['county']:10s} {r['election_date']} {r['election_type']:10s} "
          f"{r['voting_method']:15s} total={r['total']:6d} dem={r['dem']:6d} rep={r['rep']:6d} "
          f"geocoded={r['geocoded']:6d} ({pct:.1f}%) ungeo={ungeo}")

print()
print("=" * 90)
print("API /api/election-stats COMPARISON")
print("=" * 90)

# Get unique elections
elections = conn.execute('''
    SELECT DISTINCT v.county, ve.election_date, ve.voting_method
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    ORDER BY ve.election_date DESC, v.county
''').fetchall()

for e in elections:
    county = e['county']
    edate = e['election_date']
    vm = e['voting_method']

    # DB counts
    db_row = conn.execute('''
        SELECT COUNT(DISTINCT ve.vuid) as total,
               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep,
               COUNT(DISTINCT CASE WHEN v.geocoded = 1 THEN ve.vuid END) as geocoded
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ? AND ve.election_date = ? AND ve.voting_method = ?
    ''', (county, edate, vm)).fetchone()

    # API call
    url = f"http://localhost:5000/api/election-stats?county={county}&election_date={edate}&voting_method={vm}"
    try:
        resp = urllib.request.urlopen(url)
        api_data = json.loads(resp.read())
        stats = api_data.get('stats', {})

        api_total = stats.get('total', 0)
        api_dem = stats.get('democratic', 0)
        api_rep = stats.get('republican', 0)
        api_geo = stats.get('geocoded', 0)
        api_new = stats.get('new_voters', 0)
        api_flip_dem = stats.get('flipped_to_dem', 0)
        api_flip_rep = stats.get('flipped_to_rep', 0)

        total_ok = "✅" if db_row['total'] == api_total else "❌"
        dem_ok = "✅" if db_row['dem'] == api_dem else "❌"
        rep_ok = "✅" if db_row['rep'] == api_rep else "❌"
        geo_ok = "✅" if db_row['geocoded'] == api_geo else "❌"

        print(f"\n  {county} {edate} {vm}")
        print(f"    DB:  total={db_row['total']:6d}  dem={db_row['dem']:6d}  rep={db_row['rep']:6d}  geocoded={db_row['geocoded']:6d}")
        print(f"    API: total={api_total:6d}  dem={api_dem:6d}  rep={api_rep:6d}  geocoded={api_geo:6d}  new={api_new}  flip_dem={api_flip_dem}  flip_rep={api_flip_rep}")
        print(f"    Match: total={total_ok} dem={dem_ok} rep={rep_ok} geocoded={geo_ok}")

        if db_row['total'] != api_total:
            print(f"    ⚠️  TOTAL MISMATCH: DB={db_row['total']} vs API={api_total}")
        if db_row['dem'] != api_dem:
            print(f"    ⚠️  DEM MISMATCH: DB={db_row['dem']} vs API={api_dem}")
        if db_row['rep'] != api_rep:
            print(f"    ⚠️  REP MISMATCH: DB={db_row['rep']} vs API={api_rep}")
    except Exception as ex:
        print(f"\n  {county} {edate} {vm}")
        print(f"    API ERROR: {ex}")

print()
print("=" * 90)
print("CHECKING FOR DUPLICATE VUIDs IN SAME ELECTION")
print("=" * 90)
dups = conn.execute('''
    SELECT v.county, ve.election_date, ve.election_type, ve.voting_method, ve.vuid, COUNT(*) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    GROUP BY v.county, ve.election_date, ve.election_type, ve.voting_method, ve.vuid
    HAVING cnt > 1
    ORDER BY cnt DESC
    LIMIT 20
''').fetchall()
if dups:
    total_dups = conn.execute('''
        SELECT COUNT(*) as cnt FROM (
            SELECT ve.vuid FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            GROUP BY v.county, ve.election_date, ve.election_type, ve.voting_method, ve.vuid
            HAVING COUNT(*) > 1
        )
    ''').fetchone()['cnt']
    print(f"  ⚠️  Found {total_dups} duplicate VUIDs (showing top 20):")
    for d in dups:
        print(f"    {d['county']} {d['election_date']} {d['voting_method']} VUID={d['vuid']} count={d['cnt']}")
else:
    print("  ✅ No duplicate VUIDs found")

print()
print("=" * 90)
print("CHECKING election_date = '2026-02-27' (suspicious)")
print("=" * 90)
rows3 = conn.execute('''
    SELECT v.county, ve.election_type, ve.voting_method, ve.party_voted, COUNT(*) as cnt,
           ve.source_file
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-27'
    GROUP BY v.county, ve.election_type, ve.voting_method, ve.party_voted, ve.source_file
''').fetchall()
if rows3:
    for r in rows3:
        print(f"  {r['county']} {r['election_type']} {r['voting_method']} {r['party_voted']} = {r['cnt']}  source={r['source_file']}")
else:
    print("  No records for 2026-02-27")

# Check overlap between 2026-02-27 and 2026-03-03
print()
print("  Overlap check: VUIDs in both 2026-02-27 and 2026-03-03:")
overlap = conn.execute('''
    SELECT COUNT(DISTINCT a.vuid) as cnt
    FROM voter_elections a
    JOIN voter_elections b ON a.vuid = b.vuid
    WHERE a.election_date = '2026-02-27' AND b.election_date = '2026-03-03'
''').fetchone()
print(f"  VUIDs in both: {overlap['cnt']}")

# Sample some 2026-02-27 records
print()
print("  Sample 2026-02-27 records:")
samples = conn.execute('''
    SELECT ve.vuid, v.county, ve.party_voted, ve.voting_method, ve.source_file, ve.created_at
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-02-27'
    LIMIT 5
''').fetchall()
for s in samples:
    print(f"    VUID={s['vuid']} county={s['county']} party={s['party_voted']} method={s['voting_method']} source={s['source_file']} created={s['created_at']}")

conn.close()
