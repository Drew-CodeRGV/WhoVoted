#!/usr/bin/env python3
"""
Analyze D15 by county to find missing voters
"""
import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

# D15 counties (from official data)
D15_COUNTIES = ['Hidalgo', 'Brooks', 'Jim Wells', 'Bee', 'San Patricio', 'Refugio', 
                'Goliad', 'Gonzales', 'Lavaca', 'DeWitt', 'Victoria']

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=" * 80)
print("D15 COUNTY ANALYSIS")
print("=" * 80)

# Check each D15 county
print("\n1. DEMOCRATIC VOTERS BY D15 COUNTY")
print("-" * 80)

print(f"{'County':<20} {'Total Dem':>12} {'Assigned D15':>15} {'Coverage':>10}")
print("-" * 60)

total_dem = 0
total_assigned = 0

for county in D15_COUNTIES:
    # Total Democratic voters in county
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
    """, (county, ELECTION_DATE))
    
    dem_count = cursor.fetchone()[0]
    
    # Assigned to D15
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
        AND ve.congressional_district = 'TX-15'
    """, (county, ELECTION_DATE))
    
    assigned = cursor.fetchone()[0]
    
    coverage = 100 * assigned / dem_count if dem_count > 0 else 0
    
    print(f"{county:<20} {dem_count:>12,} {assigned:>15,} {coverage:>9.1f}%")
    
    total_dem += dem_count
    total_assigned += assigned

print("-" * 60)
print(f"{'TOTAL':<20} {total_dem:>12,} {total_assigned:>15,}")

# Check for unassigned voters in D15 counties
print("\n2. UNASSIGNED VOTERS IN D15 COUNTIES")
print("-" * 80)

for county in D15_COUNTIES:
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = ?
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
        AND (ve.congressional_district IS NULL OR ve.congressional_district = '')
    """, (county, ELECTION_DATE))
    
    unassigned = cursor.fetchone()[0]
    
    if unassigned > 0:
        print(f"{county:<20} {unassigned:>10,} unassigned Democratic voters")
        
        # Sample precincts
        cursor.execute("""
            SELECT DISTINCT ve.precinct, COUNT(*) as count
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE v.county = ?
            AND ve.election_date = ?
            AND ve.party_voted = 'Democratic'
            AND (ve.congressional_district IS NULL OR ve.congressional_district = '')
            AND ve.precinct IS NOT NULL
            AND ve.precinct != ''
            GROUP BY ve.precinct
            ORDER BY count DESC
            LIMIT 5
        """, (county, ELECTION_DATE))
        
        for row in cursor.fetchall():
            print(f"  Precinct '{row['precinct']}': {row['count']:,} voters")

# Check if there are D15 voters in counties we haven't considered
print("\n3. D15 VOTERS IN OTHER COUNTIES")
print("-" * 80)

cursor.execute("""
    SELECT v.county, COUNT(DISTINCT ve.vuid) as count
    FROM voter_elections ve
    JOIN voters v ON ve.vuid = v.vuid
    WHERE ve.election_date = ?
    AND ve.party_voted = 'Democratic'
    AND ve.congressional_district = 'TX-15'
    AND v.county NOT IN ({})
    GROUP BY v.county
    ORDER BY count DESC
""".format(','.join(['?' for _ in D15_COUNTIES])), (ELECTION_DATE, *D15_COUNTIES))

other_counties = cursor.fetchall()

if other_counties:
    print("Found D15 voters in unexpected counties:")
    for row in other_counties:
        print(f"  {row['county']:<20} {row['count']:>10,} voters")
else:
    print("No D15 voters found in other counties")

# Summary
print("\n" + "=" * 80)
print("SUMMARY")
print("=" * 80)

official_d15 = 54573
current_d15 = total_assigned
difference = official_d15 - current_d15

print(f"Official D15 count:        {official_d15:>10,}")
print(f"Current D15 assignment:    {current_d15:>10,}")
print(f"Difference:                {difference:>+10,}")
print(f"Accuracy:                  {100*current_d15/official_d15:>9.1f}%")

conn.close()
