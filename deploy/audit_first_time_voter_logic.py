#!/usr/bin/env python3
"""
Comprehensive audit of first-time voter logic across the system.
Shows exactly how new voters are being counted and where inconsistencies might exist.
"""

import sqlite3
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

def audit_first_time_logic():
    """Audit all first-time voter logic in the system."""
    
    print("=" * 80)
    print("FIRST-TIME VOTER LOGIC AUDIT")
    print("=" * 80)
    
    with db.get_db() as conn:
        # Get election info
        elections = conn.execute("""
            SELECT DISTINCT election_date, county
            FROM voter_elections
            ORDER BY election_date DESC, county
        """).fetchall()
        
        print(f"\nFound {len(elections)} county-election combinations")
        
        # Focus on 2026-03-03 primary
        target_election = '2026-03-03'
        
        print(f"\n{'='*80}")
        print(f"ANALYZING: {target_election} PRIMARY")
        print(f"{'='*80}")
        
        # Check prior election count
        prior_count = conn.execute("""
            SELECT COUNT(DISTINCT election_date)
            FROM voter_elections
            WHERE election_date < ?
        """, [target_election]).fetchone()[0]
        
        print(f"\nPrior elections in database: {prior_count}")
        print(f"Logic threshold: 3+ elections needed for full new voter detection")
        
        if prior_count >= 3:
            print("✓ We have enough history - using FULL logic:")
            print("  - Count 18-19 year olds (just turned 18)")
            print("  - Count voters with NO prior primary voting history")
        else:
            print("⚠ Limited history - using RESTRICTED logic:")
            print("  - Only count 18-19 year olds (just turned 18)")
            print("  - Ignore voters with no prior history (unreliable)")
        
        # Calculate birth year range
        election_year = 2026
        min_birth_year = election_year - 19  # 2007
        max_birth_year = election_year - 18  # 2008
        
        print(f"\n18-19 year old range: birth years {min_birth_year}-{max_birth_year}")
        
        # Get county-by-county breakdown
        counties = conn.execute("""
            SELECT DISTINCT v.county
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = ?
            ORDER BY v.county
        """, [target_election]).fetchall()
        
        print(f"\n{'='*80}")
        print("COUNTY-BY-COUNTY BREAKDOWN")
        print(f"{'='*80}")
        
        for county_row in counties:
            county = county_row[0]
            
            print(f"\n{county} County:")
            print("-" * 40)
            
            # Check if county has prior data
            has_prior = conn.execute("""
                SELECT 1 FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE v.county = ?
                  AND ve.election_date < ?
                  AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
                LIMIT 1
            """, (county, target_election)).fetchone()
            
            has_prior_data = has_prior is not None
            
            print(f"Has prior election data: {has_prior_data}")
            
            # Total voters in this election
            total = conn.execute("""
                SELECT COUNT(*)
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE v.county = ? AND ve.election_date = ?
            """, [county, target_election]).fetchone()[0]
            
            print(f"Total voters in {target_election}: {total:,}")
            
            # Count by method 1: is_new_voter flag (set during processing)
            flagged_new = conn.execute("""
                SELECT COUNT(*)
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE v.county = ? AND ve.election_date = ?
                  AND ve.is_new_voter = 1
            """, [county, target_election]).fetchone()[0]
            
            print(f"\nMethod 1 (is_new_voter flag): {flagged_new:,}")
            
            # Count by method 2: 18-19 year olds only
            young_voters = conn.execute("""
                SELECT COUNT(*)
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE v.county = ? AND ve.election_date = ?
                  AND v.birth_year BETWEEN ? AND ?
            """, [county, target_election, min_birth_year, max_birth_year]).fetchone()[0]
            
            print(f"Method 2 (18-19 year olds only): {young_voters:,}")
            
            # Count by method 3: No prior voting history (if we have 3+ elections)
            if prior_count >= 3:
                no_prior = conn.execute("""
                    SELECT COUNT(*)
                    FROM voter_elections ve
                    JOIN voters v ON ve.vuid = v.vuid
                    WHERE v.county = ? AND ve.election_date = ?
                      AND NOT EXISTS (
                        SELECT 1 FROM voter_elections ve2
                        WHERE ve2.vuid = ve.vuid
                          AND ve2.election_date < ?
                          AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
                      )
                """, [county, target_election, target_election]).fetchone()[0]
                
                print(f"Method 3 (no prior history): {no_prior:,}")
                
                # Combined logic (18-19 OR no prior)
                combined = conn.execute("""
                    SELECT COUNT(*)
                    FROM voter_elections ve
                    JOIN voters v ON ve.vuid = v.vuid
                    WHERE v.county = ? AND ve.election_date = ?
                      AND (
                        v.birth_year BETWEEN ? AND ?
                        OR NOT EXISTS (
                            SELECT 1 FROM voter_elections ve2
                            WHERE ve2.vuid = ve.vuid
                              AND ve2.election_date < ?
                              AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
                        )
                      )
                """, [county, target_election, min_birth_year, max_birth_year, target_election]).fetchone()[0]
                
                print(f"Method 4 (18-19 OR no prior): {combined:,}")
                
                # Check for discrepancies
                if flagged_new != combined:
                    print(f"\n⚠ DISCREPANCY: Flag count ({flagged_new:,}) != Combined logic ({combined:,})")
                    print(f"   Difference: {abs(flagged_new - combined):,} voters")
            else:
                # Limited history - should only count young voters
                if flagged_new != young_voters:
                    print(f"\n⚠ DISCREPANCY: Flag count ({flagged_new:,}) != Young voters ({young_voters:,})")
                    print(f"   Difference: {abs(flagged_new - young_voters):,} voters")
            
            # Party breakdown
            dem_new = conn.execute("""
                SELECT COUNT(*)
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE v.county = ? AND ve.election_date = ?
                  AND ve.is_new_voter = 1
                  AND ve.party_voted = 'Democratic'
            """, [county, target_election]).fetchone()[0]
            
            rep_new = conn.execute("""
                SELECT COUNT(*)
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE v.county = ? AND ve.election_date = ?
                  AND ve.is_new_voter = 1
                  AND ve.party_voted = 'Republican'
            """, [county, target_election]).fetchone()[0]
            
            print(f"\nParty breakdown (using flag):")
            print(f"  Democratic: {dem_new:,}")
            print(f"  Republican: {rep_new:,}")
            
            # Sample some flagged new voters to verify
            print(f"\nSample of flagged new voters:")
            samples = conn.execute("""
                SELECT v.vuid, v.firstname, v.lastname, v.birth_year, ve.party_voted
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE v.county = ? AND ve.election_date = ?
                  AND ve.is_new_voter = 1
                ORDER BY RANDOM()
                LIMIT 5
            """, [county, target_election]).fetchall()
            
            for s in samples:
                vuid, fname, lname, birth_year, party = s
                age = 2026 - (birth_year or 0)
                
                # Check their actual history
                history = conn.execute("""
                    SELECT election_date, party_voted
                    FROM voter_elections
                    WHERE vuid = ?
                    ORDER BY election_date
                """, [vuid]).fetchall()
                
                print(f"  {fname} {lname} (age {age}, {party})")
                print(f"    History: {len(history)} elections")
                for h in history:
                    print(f"      {h[0]}: {h[1]}")
        
        print(f"\n{'='*80}")
        print("SUMMARY OF LOGIC LOCATIONS")
        print(f"{'='*80}")
        print("""
1. database.py:780 - Sets is_new_voter flag during GeoJSON generation
   Logic: (vuid not in prior_vuids) if has_prior else False
   - Checks _county_has_prior_data() first
   - Only flags if county has data before this election

2. database.py:1123 - Calculates new_voters for stats
   Logic: NOT EXISTS (prior election with party_voted)
   - Then zeros out if !_county_has_prior_data()

3. app.py:1259 & reports.py:449 - API endpoint calculations
   Logic: If 3+ prior elections:
     - 18-19 year olds OR no prior voting history
   Else:
     - Only 18-19 year olds

4. processor.py:1616 - Sets is_new_voter during CSV import
   Logic: (vuid not in prior_vuids) if has_prior_data else False

POTENTIAL ISSUES:
- Different logic in different places (simple NOT EXISTS vs age-based)
- Flag set during processing may not match runtime calculations
- County-level prior data check may give false negatives
        """)

if __name__ == '__main__':
    audit_first_time_logic()
