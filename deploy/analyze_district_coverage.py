#!/usr/bin/env python3
"""Analyze actual district coverage - counties and precincts with voting data."""

import sqlite3
import json
from collections import defaultdict

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
        
        # 1. Get ALL voters assigned to this district (regardless of voting status)
        total_in_district = conn.execute("""
            SELECT COUNT(*) as count
            FROM voters
            WHERE congressional_district = ?
        """, (district_num,)).fetchone()['count']
        
        print(f"Total voters assigned to district: {total_in_district:,}")
        
        # 2. Get voters who VOTED in 2026 primary
        voted_2026 = conn.execute("""
            SELECT COUNT(DISTINCT v.vuid) as count
            FROM voters v
            JOIN voter_elections ve ON v.vuid = ve.vuid
            WHERE v.congressional_district = ?
            AND ve.election_date = '2026-03-03'
        """, (district_num,)).fetchone()['count']
        
        print(f"Voters who voted in 2026 primary: {voted_2026:,}")
        print()
        
        # 3. Get COUNTY breakdown for ALL voters in district
        print("COUNTIES IN DISTRICT (all registered voters):")
        print("-" * 60)
        county_rows = conn.execute("""
            SELECT county, COUNT(*) as total_voters
            FROM voters
            WHERE congressional_district = ?
            AND county IS NOT NULL AND county != ''
            GROUP BY county
            ORDER BY total_voters DESC
        """, (district_num,)).fetchall()
        
        total_counties = len(county_rows)
        for row in county_rows:
            print(f"  {row['county']:20s} {row['total_voters']:>10,} voters")
        
        print(f"\nTotal counties: {total_counties}")
        print()
        
        # 4. Get COUNTY breakdown for voters who VOTED in 2026
        print("COUNTIES WITH 2026 VOTING DATA:")
        print("-" * 60)
        county_voted_rows = conn.execute("""
            SELECT v.county, 
                   COUNT(DISTINCT v.vuid) as voters_who_voted,
                   COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN v.vuid END) as dem,
                   COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN v.vuid END) as rep
            FROM voters v
            JOIN voter_elections ve ON v.vuid = ve.vuid
            WHERE v.congressional_district = ?
            AND ve.election_date = '2026-03-03'
            AND v.county IS NOT NULL AND v.county != ''
            GROUP BY v.county
            ORDER BY voters_who_voted DESC
        """, (district_num,)).fetchall()
        
        counties_with_data = len(county_voted_rows)
        for row in county_voted_rows:
            pct = (row['voters_who_voted'] / voted_2026 * 100) if voted_2026 > 0 else 0
            print(f"  {row['county']:20s} {row['voters_who_voted']:>8,} voted ({pct:>5.1f}%) - D:{row['dem']:>6,} R:{row['rep']:>6,}")
        
        print(f"\nCounties with voting data: {counties_with_data}")
        print()
        
        # 5. Get PRECINCT breakdown for ALL voters in district
        print("PRECINCTS IN DISTRICT (all registered voters):")
        print("-" * 60)
        precinct_rows = conn.execute("""
            SELECT precinct, county, COUNT(*) as total_voters
            FROM voters
            WHERE congressional_district = ?
            AND precinct IS NOT NULL AND precinct != ''
            GROUP BY precinct, county
            ORDER BY total_voters DESC
            LIMIT 20
        """, (district_num,)).fetchall()
        
        total_precincts = conn.execute("""
            SELECT COUNT(DISTINCT precinct) as count
            FROM voters
            WHERE congressional_district = ?
            AND precinct IS NOT NULL AND precinct != ''
        """, (district_num,)).fetchone()['count']
        
        print(f"Top 20 precincts by registered voters:")
        for row in precinct_rows:
            print(f"  {row['precinct']:15s} ({row['county']:15s}) {row['total_voters']:>8,} voters")
        
        print(f"\nTotal precincts in district: {total_precincts}")
        print()
        
        # 6. Get PRECINCT breakdown for voters who VOTED in 2026
        print("PRECINCTS WITH 2026 VOTING DATA:")
        print("-" * 60)
        precinct_voted_rows = conn.execute("""
            SELECT v.precinct, v.county, COUNT(DISTINCT v.vuid) as voters_who_voted
            FROM voters v
            JOIN voter_elections ve ON v.vuid = ve.vuid
            WHERE v.congressional_district = ?
            AND ve.election_date = '2026-03-03'
            AND v.precinct IS NOT NULL AND v.precinct != ''
            GROUP BY v.precinct, v.county
            ORDER BY voters_who_voted DESC
            LIMIT 20
        """, (district_num,)).fetchall()
        
        precincts_with_data = conn.execute("""
            SELECT COUNT(DISTINCT v.precinct) as count
            FROM voters v
            JOIN voter_elections ve ON v.vuid = ve.vuid
            WHERE v.congressional_district = ?
            AND ve.election_date = '2026-03-03'
            AND v.precinct IS NOT NULL AND v.precinct != ''
        """, (district_num,)).fetchone()['count']
        
        print(f"Top 20 precincts by 2026 turnout:")
        for row in precinct_voted_rows:
            print(f"  {row['precinct']:15s} ({row['county']:15s}) {row['voters_who_voted']:>8,} voted")
        
        print(f"\nPrecincts with voting data: {precincts_with_data}")
        print()
        
        # 7. Summary
        print("SUMMARY:")
        print("-" * 60)
        print(f"Total counties in district:           {total_counties}")
        print(f"Counties with 2026 voting data:       {counties_with_data}")
        print(f"Counties missing data:                {total_counties - counties_with_data}")
        print()
        print(f"Total precincts in district:          {total_precincts}")
        print(f"Precincts with 2026 voting data:      {precincts_with_data}")
        print(f"Precincts missing data:               {total_precincts - precincts_with_data}")
        print()
        
        # 8. Check for voters WITHOUT county assignment
        no_county = conn.execute("""
            SELECT COUNT(*) as count
            FROM voters
            WHERE congressional_district = ?
            AND (county IS NULL OR county = '')
        """, (district_num,)).fetchone()['count']
        
        if no_county > 0:
            print(f"⚠️  WARNING: {no_county:,} voters in district have NO county assigned!")
            print()
        
        # 9. Check for voters WITHOUT precinct assignment
        no_precinct = conn.execute("""
            SELECT COUNT(*) as count
            FROM voters
            WHERE congressional_district = ?
            AND (precinct IS NULL OR precinct = '')
        """, (district_num,)).fetchone()['count']
        
        if no_precinct > 0:
            print(f"⚠️  WARNING: {no_precinct:,} voters in district have NO precinct assigned!")
            print()
    
    conn.close()

if __name__ == '__main__':
    analyze_districts()
