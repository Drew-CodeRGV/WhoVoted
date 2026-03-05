#!/usr/bin/env python3
"""
Check why first-time voter numbers are so high.
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

print("Analyzing First-Time Voter Logic")
print("=" * 80)

# Overall stats for 2026
overall = conn.execute("""
    SELECT 
        COUNT(DISTINCT ve.vuid) as total_voters,
        SUM(CASE WHEN ve.is_new_voter = 1 THEN 1 ELSE 0 END) as new_voters,
        SUM(CASE WHEN ve.is_new_voter = 0 THEN 1 ELSE 0 END) as returning_voters
    FROM voter_elections ve
    WHERE ve.election_date = '2026-03-03'
""").fetchone()

print(f"\nOverall 2026 Stats:")
print(f"  Total voters: {overall['total_voters']:,}")
print(f"  New voters: {overall['new_voters']:,} ({overall['new_voters']/overall['total_voters']*100:.1f}%)")
print(f"  Returning: {overall['returning_voters']:,}")

# Sample some "new" voters
print("\n" + "=" * 80)
print("Sample of voters marked as 'new':")
print("=" * 80)

samples = conn.execute("""
    SELECT 
        v.vuid,
        v.birth_year,
        v.county,
        ve.is_new_voter,
        (2026 - v.birth_year) as age_in_2026,
        (SELECT COUNT(*) FROM voter_elections ve2 
         WHERE ve2.vuid = v.vuid AND ve2.election_date < '2026-03-03'
           AND ve2.party_voted IN ('Democratic', 'Republican')) as prior_elections
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
      AND ve.is_new_voter = 1
    LIMIT 30
""").fetchall()

for s in samples:
    age = s['age_in_2026'] if s['birth_year'] else 'Unknown'
    print(f"VUID: {s['vuid'][:20]}...")
    print(f"  Age: {age}, County: {s['county']}, Prior elections: {s['prior_elections']}")
    
    # Check if they were eligible in prior elections
    if s['birth_year']:
        was_18_in_2024 = (2024 - s['birth_year']) >= 18
        was_18_in_2022 = (2022 - s['birth_year']) >= 18
        print(f"  Was 18+ in 2024? {was_18_in_2024}, in 2022? {was_18_in_2022}")
        
        # If they're 30+ and have no prior history, that's suspicious
        if age != 'Unknown' and age >= 30 and s['prior_elections'] == 0:
            print(f"  ⚠️  SUSPICIOUS: {age} years old with no prior history")
    print()

# Age distribution
print("=" * 80)
print("Age distribution of 'new' voters:")
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

total_new = sum(ad['cnt'] for ad in age_dist)
for ad in age_dist:
    pct = (ad['cnt'] / total_new * 100) if total_new > 0 else 0
    print(f"  {ad['age_group']:10s}: {ad['cnt']:8,} ({pct:5.1f}%)")

# Check county prior election coverage
print("\n" + "=" * 80)
print("Prior election coverage by county (top 10):")
print("=" * 80)

county_coverage = conn.execute("""
    SELECT 
        v.county,
        COUNT(DISTINCT ve.vuid) as voters_2026,
        SUM(CASE WHEN ve.is_new_voter = 1 THEN 1 ELSE 0 END) as new_voters,
        (SELECT COUNT(DISTINCT ve2.election_date) 
         FROM voter_elections ve2
         JOIN voters v2 ON ve2.vuid = v2.vuid
         WHERE v2.county = v.county 
           AND ve2.election_date < '2026-03-03'
           AND ve2.party_voted IN ('Democratic', 'Republican')) as prior_election_count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = '2026-03-03'
    GROUP BY v.county
    ORDER BY voters_2026 DESC
    LIMIT 10
""").fetchall()

for cc in county_coverage:
    new_pct = (cc['new_voters'] / cc['voters_2026'] * 100) if cc['voters_2026'] > 0 else 0
    print(f"{cc['county']}:")
    print(f"  2026 voters: {cc['voters_2026']:,}, New: {cc['new_voters']:,} ({new_pct:.1f}%)")
    print(f"  Prior elections in DB: {cc['prior_election_count']}")
    print()

conn.close()
