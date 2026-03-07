#!/usr/bin/env python3
"""
Diagnose why D15 precincts aren't matching.
Show what precinct formats exist in both the reference data and voting records.
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 70)
print("PRECINCT FORMAT DIAGNOSIS")
print("=" * 70)

# D15 counties
d15_counties = ['Hidalgo', 'Brooks', 'Jim Wells', 'Bee', 'San Patricio', 'Refugio']

for county in d15_counties:
    print(f"\n{'='*70}")
    print(f"{county} County")
    print(f"{'='*70}")
    
    # Check if this county has precinct mappings in precinct_districts
    cursor.execute("""
        SELECT COUNT(*), COUNT(DISTINCT precinct)
        FROM precinct_districts
        WHERE county = ? AND congressional_district = 'TX-15'
    """, (county,))
    
    mapping_count, unique_precincts = cursor.fetchone()
    print(f"\nReference Data (precinct_districts table):")
    print(f"  Mappings: {mapping_count}")
    print(f"  Unique precincts: {unique_precincts}")
    
    if unique_precincts > 0:
        cursor.execute("""
            SELECT DISTINCT precinct
            FROM precinct_districts
            WHERE county = ? AND congressional_district = 'TX-15'
            ORDER BY precinct
            LIMIT 10
        """, (county,))
        
        print(f"  Sample precincts:")
        for (precinct,) in cursor.fetchall():
            print(f"    '{precinct}'")
    
    # Check voting records for this county
    cursor.execute("""
        SELECT COUNT(*), COUNT(DISTINCT precinct)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
        AND ve.precinct IS NOT NULL
        AND ve.precinct != ''
    """, (county, ELECTION_DATE))
    
    vote_count, vote_precincts = cursor.fetchone()
    print(f"\nVoting Records (voter_elections table):")
    print(f"  Democratic voters: {vote_count:,}")
    print(f"  Unique precincts: {vote_precincts}")
    
    if vote_precincts > 0:
        cursor.execute("""
            SELECT DISTINCT ve.precinct, COUNT(*) as count
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE v.county = ?
            AND ve.election_date = ?
            AND ve.party_voted = 'Democratic'
            AND ve.precinct IS NOT NULL
            AND ve.precinct != ''
            GROUP BY ve.precinct
            ORDER BY count DESC
            LIMIT 10
        """, (county, ELECTION_DATE))
        
        print(f"  Top precincts by voter count:")
        for precinct, count in cursor.fetchall():
            print(f"    '{precinct}' - {count:,} voters")

# Overall D15 stats
print(f"\n{'='*70}")
print("D15 OVERALL")
print(f"{'='*70}")

cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county IN ('Hidalgo', 'Brooks', 'Jim Wells', 'Bee', 'San Patricio', 'Refugio')
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
""", (ELECTION_DATE,))

total_d15_voters = cursor.fetchone()[0]
print(f"\nTotal Democratic voters in D15 counties: {total_d15_voters:,}")
print(f"Official D15 count: 54,573")
print(f"Difference: {total_d15_voters - 54573:+,}")

# Check how many have precincts
cursor.execute("""
    SELECT COUNT(DISTINCT ve.vuid)
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE v.county IN ('Hidalgo', 'Brooks', 'Jim Wells', 'Bee', 'San Patricio', 'Refugio')
    AND ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.precinct IS NOT NULL
    AND ve.precinct != ''
""", (ELECTION_DATE,))

with_precinct = cursor.fetchone()[0]
print(f"Voters with precinct data: {with_precinct:,} ({100*with_precinct/total_d15_voters:.1f}%)")

conn.close()
