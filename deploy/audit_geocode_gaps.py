#!/usr/bin/env python3
"""Audit geocode gaps across all datasets."""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("=" * 90)
print("GEOCODE RATE AUDIT — ALL DATASETS")
print("=" * 90)

rows = conn.execute("""
    SELECT 
        ve.election_date,
        ve.voting_method,
        ve.party_voted,
        COALESCE(v.county, 'Unknown') as county,
        COUNT(DISTINCT ve.vuid) as total,
        SUM(CASE WHEN v.geocoded = 1 THEN 1 ELSE 0 END) as geocoded,
        SUM(CASE WHEN v.geocoded != 1 OR v.geocoded IS NULL THEN 1 ELSE 0 END) as not_geocoded,
        ve.source_file
    FROM voter_elections ve
    LEFT JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.party_voted != '' AND ve.party_voted IS NOT NULL
    GROUP BY ve.election_date, ve.voting_method, ve.party_voted, COALESCE(v.county, 'Unknown')
    ORDER BY ve.election_date DESC, ve.voting_method, ve.party_voted
""").fetchall()

for r in rows:
    total = r['total']
    geo = r['geocoded']
    miss = r['not_geocoded']
    rate = (geo / total * 100) if total > 0 else 0
    flag = " ⚠️" if rate < 100 else ""
    fn = (r['source_file'] or '—')[:50]
    print(f"  {r['election_date']}  {r['county']:8s}  {r['voting_method']:15s}  {r['party_voted']:12s}  "
          f"total={total:>6,}  geo={geo:>6,}  miss={miss:>5,}  rate={rate:5.1f}%{flag}")

# Detailed look at the misses for 2026
print("\n" + "=" * 90)
print("2026 HIDALGO — UNGEOCODED VOTERS DETAIL")
print("=" * 90)

# How many ungeocoded voters are there total?
row = conn.execute("""
    SELECT COUNT(DISTINCT ve.vuid) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
      AND (v.geocoded != 1 OR v.geocoded IS NULL)
""").fetchone()
print(f"\nTotal ungeocoded Hidalgo 2026 voters: {row['cnt']}")

# Do they have addresses?
row2 = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as total_ungeo,
        SUM(CASE WHEN v.address IS NOT NULL AND v.address != '' THEN 1 ELSE 0 END) as has_addr,
        SUM(CASE WHEN v.address IS NULL OR v.address = '' THEN 1 ELSE 0 END) as no_addr
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
      AND (v.geocoded != 1 OR v.geocoded IS NULL)
""").fetchone()
print(f"  With address: {row2['has_addr']}")
print(f"  No address:   {row2['no_addr']}")

# By voting method
print("\nBy voting method:")
rows3 = conn.execute("""
    SELECT 
        ve.voting_method,
        ve.party_voted,
        COUNT(DISTINCT ve.vuid) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
      AND (v.geocoded != 1 OR v.geocoded IS NULL)
    GROUP BY ve.voting_method, ve.party_voted
    ORDER BY ve.voting_method, ve.party_voted
""").fetchall()
for r in rows3:
    print(f"  {r['voting_method']:15s}  {r['party_voted']:12s}  {r['cnt']:>5,}")

# Sample some ungeocoded voters
print("\nSample ungeocoded voters:")
samples = conn.execute("""
    SELECT v.vuid, v.firstname, v.lastname, v.address, v.city, v.zip, v.lat, v.lng, v.geocoded, v.source
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county = 'Hidalgo' AND ve.election_date = '2026-03-03'
      AND (v.geocoded != 1 OR v.geocoded IS NULL)
    LIMIT 10
""").fetchall()
for s in samples:
    addr = s['address'] or '(none)'
    if len(addr) > 50:
        addr = addr[:47] + '...'
    print(f"  VUID={s['vuid']}  {s['firstname'] or ''} {s['lastname'] or ''}  addr={addr}  "
          f"lat={s['lat']}  geocoded={s['geocoded']}  source={s['source'] or '?'}")

conn.close()
