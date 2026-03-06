#!/usr/bin/env python3
"""Determine which counties a district covers by looking at assigned voters.

Since we've already assigned voters to districts using point-in-polygon checks,
we can simply look at which counties have voters assigned to each district.
"""

import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

def determine_counties_in_district(district_num):
    """Determine which counties have voters assigned to a district."""
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    print(f"\n{'='*80}")
    print(f"TX-{district_num} CONGRESSIONAL DISTRICT - COUNTY COVERAGE")
    print(f"{'='*80}\n")
    
    # Get all counties that have voters assigned to this district
    county_rows = conn.execute("""
        SELECT county, 
               COUNT(*) as total_voters,
               SUM(CASE WHEN geocoded = 1 THEN 1 ELSE 0 END) as geocoded_voters
        FROM voters
        WHERE congressional_district = ?
        AND county IS NOT NULL
        AND county != ''
        GROUP BY county
        ORDER BY total_voters DESC
    """, (district_num,)).fetchall()
    
    total_voters_in_district = sum(row['total_voters'] for row in county_rows)
    
    print(f"Counties with voters assigned to TX-{district_num}:\n")
    for i, row in enumerate(county_rows, 1):
        pct = (row['total_voters'] / total_voters_in_district * 100) if total_voters_in_district > 0 else 0
        print(f"  {i}. {row['county']:20s} {row['total_voters']:>8,} voters ({pct:>5.1f}%) - {row['geocoded_voters']:>8,} geocoded")
    
    print(f"\nTotal counties: {len(county_rows)}")
    print(f"Total voters in district: {total_voters_in_district:,}")
    
    # Also check how many voters in this district have voted in 2026
    voters_2026 = conn.execute("""
        SELECT v.county,
               COUNT(DISTINCT v.vuid) as voters_who_voted
        FROM voters v
        JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.congressional_district = ?
        AND ve.election_date = '2026-03-03'
        AND v.county IS NOT NULL
        AND v.county != ''
        GROUP BY v.county
        ORDER BY voters_who_voted DESC
    """, (district_num,)).fetchall()
    
    total_voted_2026 = sum(row['voters_who_voted'] for row in voters_2026)
    
    print(f"\n{'='*80}")
    print(f"2026 PRIMARY ELECTION TURNOUT BY COUNTY")
    print(f"{'='*80}\n")
    
    for i, row in enumerate(voters_2026, 1):
        pct = (row['voters_who_voted'] / total_voted_2026 * 100) if total_voted_2026 > 0 else 0
        print(f"  {i}. {row['county']:20s} {row['voters_who_voted']:>8,} voted ({pct:>5.1f}%)")
    
    print(f"\nCounties with 2026 data: {len(voters_2026)}")
    print(f"Total voters who voted in 2026: {total_voted_2026:,}")
    print()
    
    conn.close()
    
    return len(county_rows), county_rows

if __name__ == '__main__':
    for district_num in ['15', '28', '34']:
        determine_counties_in_district(district_num)
