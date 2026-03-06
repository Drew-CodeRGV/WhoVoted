#!/usr/bin/env python3
"""Fast analysis of district coverage - counties and precincts with voting data."""

import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

def analyze_districts():
    """Analyze each congressional district to see actual coverage."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    districts = ['15', '28', '34']
    
    print("=" * 80)
    print("DISTRICT COVERAGE ANALYSIS - 2026 PRIMARY ELECTION")
    print("=" * 80)
    print()
    
    for district_num in districts:
        print(f"\n{'=' * 80}")
        print(f"TX-{district_num} CONGRESSIONAL DISTRICT")
        print(f"{'=' * 80}\n")
        
        # Get voters who VOTED in 2026 primary with county/precinct info
        print("COUNTIES WITH 2026 VOTING DATA:")
        print("-" * 60)
        county_voted_rows = conn.execute("""
            SELECT v.county, 
                   COUNT(DISTINCT v.vuid) as voters_who_voted,
                   SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
                   SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep
            FROM voters v
            JOIN voter_elections ve ON v.vuid = ve.vuid
            WHERE v.congressional_district = ?
            AND ve.election_date = '2026-03-03'
            AND v.county IS NOT NULL AND v.county != ''
            GROUP BY v.county
            ORDER BY voters_who_voted DESC
        """, (district_num,)).fetchall()
        
        total_voted = sum(row['voters_who_voted'] for row in county_voted_rows)
        counties_with_data = len(county_voted_rows)
        
        for row in county_voted_rows:
            pct = (row['voters_who_voted'] / total_voted * 100) if total_voted > 0 else 0
            print(f"  {row['county']:20s} {row['voters_who_voted']:>8,} voted ({pct:>5.1f}%) - D:{row['dem']:>6,} R:{row['rep']:>6,}")
        
        print(f"\nTotal voters who voted in 2026: {total_voted:,}")
        print(f"Counties with voting data: {counties_with_data}")
        print()
        
        # Get PRECINCT count
        print("PRECINCTS WITH 2026 VOTING DATA:")
        print("-" * 60)
        
        precincts_with_data = conn.execute("""
            SELECT COUNT(DISTINCT v.precinct) as count
            FROM voters v
            JOIN voter_elections ve ON v.vuid = ve.vuid
            WHERE v.congressional_district = ?
            AND ve.election_date = '2026-03-03'
            AND v.precinct IS NOT NULL AND v.precinct != ''
        """, (district_num,)).fetchone()['count']
        
        # Get precinct breakdown by county
        precinct_by_county = conn.execute("""
            SELECT v.county, COUNT(DISTINCT v.precinct) as precinct_count
            FROM voters v
            JOIN voter_elections ve ON v.vuid = ve.vuid
            WHERE v.congressional_district = ?
            AND ve.election_date = '2026-03-03'
            AND v.precinct IS NOT NULL AND v.precinct != ''
            AND v.county IS NOT NULL AND v.county != ''
            GROUP BY v.county
            ORDER BY precinct_count DESC
        """, (district_num,)).fetchall()
        
        for row in precinct_by_county:
            print(f"  {row['county']:20s} {row['precinct_count']:>4} precincts with data")
        
        print(f"\nTotal precincts with voting data: {precincts_with_data}")
        print()
        
        # Summary
        print("SUMMARY:")
        print("-" * 60)
        print(f"Counties with 2026 voting data:       {counties_with_data}")
        print(f"Precincts with 2026 voting data:      {precincts_with_data}")
        print(f"Total voters who voted in 2026:       {total_voted:,}")
        print()
    
    conn.close()

if __name__ == '__main__':
    analyze_districts()
