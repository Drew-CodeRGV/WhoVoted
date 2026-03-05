#!/usr/bin/env python3
"""
Check first-time voter logic for TX-15 Congressional District.
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("Analyzing TX-15 First-Time Voters")
print("=" * 80)

# Get TX-15 stats
tx15_stats = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as total_voters,
        SUM(CASE WHEN ve.is_new_voter = 1 THEN 1 ELSE 0 END) as new_voters,
        SUM(CASE WHEN ve.is_new_voter = 0 THEN 1 ELSE 0 END) as returning_voters
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND v.tx_house_district = '15'
""").fetchone()

print(f"\nTX-15 Overall Stats:")
print(f"  Total voters: {tx15_stats['total_voters']:,}")
print(f"  New voters: {tx15_stats['new_voters']:,} ({tx15_stats['new_voters']/tx15_stats['total_voters']*100:.1f}%)")
print(f"  Returning: {tx15_stats['returning_voters']:,} ({tx15_stats['returning_voters']/tx15_stats['total_voters']*100:.1f}%)")

# Sample some "new" voters to see why they're marked as new
print("\n" + "=" * 80)
print("Sample of voters marked as 'new' in TX-15:")
print("=" * 80)

samples = conn.execute("""
    SELECT 
        v.vuid,
        v.birth_year,
        v.county,
        ve.is_new_voter,
        (2026 - v.birth_year) as age_in_2026,
        (SELECT COUNT(*) FROM voter_elections ve2 
         WHERE ve2.vuid = v.vuid AND ve2.election_date < '2026-03-03') as prior_elections
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND v.tx_house_district = '15'
      AND ve.is_new_voter = 1
    LIMIT 20
""").fetchall()

for s in samples:
    age = s['age_in_2026'] if s['birth_year'] else 'Unknown'
    print(f"VUID: {s['vuid']}")
    print(f"  Age: {age}, County: {s['county']}, Prior elections: {s['prior_elections']}")
    
    # Check if they were eligible in prior elections
    if s['birth_year']:
        was_18_in_2024 = (2024 - s['birth_year']) >= 18
        was_18_in_2022 = (2022 - s['birth_year']) >= 18
        print(f"  Was 18+ in 2024? {was_18_in_2024}, in 2022? {was_18_in_2022}")
    print()

# Check county history
print("=" * 80)
print("Prior election history by county in TX-15:")
print("=" * 80)

county_history = conn.execute("""
    SELECT 
        v.county,
        COUNT(DISTINCT v.vuid) as voters_2026,
        COUNT(DISTINCT CASE WHEN ve_prior.vuid IS NOT NULL THEN v.vuid END) as has_prior_data,
        (SELECT COUNT(DISTINCT ve2.election_date) 
         FROM voter_elections ve2
         JOIN voters v2 ON ve2.vuid = v2.vuid
         WHERE v2.county = v.county 
           AND ve2.election_date < '2026-03-03'
           AND ve2.party_voted IN ('Democratic', 'Republican')) as prior_election_count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    LEFT JOIN voter_elections ve_prior ON v.vuid = ve_prior.vuid 
        AND ve_prior.election_date < '2026-03-03'
    WHERE ve.election_date = '2026-03-03'
      AND v.tx_house_district = '15'
    GROUP BY v.county
    ORDER BY voters_2026 DESC
""").fetchall()

for ch in county_history:
    pct_with_history = (ch['has_prior_data'] / ch['voters_2026'] * 100) if ch['voters_2026'] > 0 else 0
    print(f"{ch['county']}:")
    print(f"  2026 voters: {ch['voters_2026']:,}")
    print(f"  With prior history: {ch['has_prior_data']:,} ({pct_with_history:.1f}%)")
    print(f"  Prior elections in DB: {ch['prior_election_count']}")
    print()

# Check age distribution of "new" voters
print("=" * 80)
print("Age distribution of 'new' voters in TX-15:")
print("=" * 80)

age_dist = conn.execute("""
    SELECT 
        CASE
            WHEN v.birth_year IS NULL THEN 'Unknown'
            WHEN (2026 - v.birth_year) < 25 THEN '18-24'
            WHEN (2026 - v.birth_year) < 35 THEN '25-34'
            WHEN (2026 - v.birth_year) < 45 THEN '35-44'
            WHEN (2026 - v.birth_year) < 55 THEN '45-54'
            WHEN (2026 - v.birth_year) < 65 THEN '55-64'
            ELSE '65+'
        END as age_group,
        COUNT(*) as cnt
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND v.tx_house_district = '15'
      AND ve.is_new_voter = 1
    GROUP BY age_group
    ORDER BY 
        CASE age_group
            WHEN '18-24' THEN 1
            WHEN '25-34' THEN 2
            WHEN '35-44' THEN 3
            WHEN '45-54' THEN 4
            WHEN '55-64' THEN 5
            WHEN '65+' THEN 6
            ELSE 7
        END
""").fetchall()

for ad in age_dist:
    print(f"  {ad['age_group']}: {ad['cnt']:,}")

conn.close()
