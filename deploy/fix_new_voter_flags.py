#!/usr/bin/env python3
"""
Recalculate is_new_voter flags using the new conservative logic.

Rule 1: Voter was under 18 for all prior elections (newly eligible)
Rule 2: County has 3+ prior elections AND voter has no prior history AND we have their birth year

CRITICAL: If we don't have birth year data, we CANNOT mark as new voter.
This prevents false positives from statewide EVR data that lacks birth years.

Better safe than sorry - if we don't have sufficient data, don't mark as new.
"""

import sqlite3
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

def fix_new_voter_flags():
    """Recalculate all is_new_voter flags with new logic."""
    
    print("=" * 80)
    print("RECALCULATING FIRST-TIME VOTER FLAGS")
    print("=" * 80)
    
    with db.get_db() as conn:
        # Get all elections
        elections = conn.execute("""
            SELECT DISTINCT election_date
            FROM voter_elections
            ORDER BY election_date DESC
        """).fetchall()
        
        print(f"\nFound {len(elections)} elections to process")
        
        for election_row in elections:
            election_date = election_row[0]
            print(f"\n{'='*80}")
            print(f"Processing: {election_date}")
            print(f"{'='*80}")
            
            # Get counties for this election
            counties = conn.execute("""
                SELECT DISTINCT v.county, COUNT(*) as voters
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE ve.election_date = ?
                GROUP BY v.county
                ORDER BY v.county
            """, [election_date]).fetchall()
            
            for county_row in counties:
                county, voter_count = county_row
                print(f"\n{county} County ({voter_count:,} voters):")
                
                # Check how many prior elections this county has
                prior_count = conn.execute("""
                    SELECT COUNT(DISTINCT ve.election_date)
                    FROM voter_elections ve
                    JOIN voters v ON ve.vuid = v.vuid
                    WHERE v.county = ?
                      AND ve.election_date < ?
                      AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
                """, [county, election_date]).fetchone()[0]
                
                print(f"  Prior elections: {prior_count}")
                
                if prior_count >= 3:
                    print(f"  ✓ Sufficient history - applying Rule 2 (no prior history + known age)")
                    
                    # Rule 2: County has 3+ prior elections
                    # Mark as new ONLY if:
                    # - Voter has no prior history AND
                    # - We have their birth year (can verify they were eligible)
                    updated = conn.execute("""
                        UPDATE voter_elections
                        SET is_new_voter = CASE
                            WHEN EXISTS (
                                SELECT 1 FROM voter_elections ve2
                                WHERE ve2.vuid = voter_elections.vuid
                                  AND ve2.election_date < ?
                                  AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
                            ) THEN 0
                            WHEN vuid IN (
                                SELECT v.vuid FROM voters v
                                WHERE v.county = ?
                                  AND v.birth_year IS NOT NULL
                                  AND v.birth_year > 0
                            ) THEN 1
                            ELSE 0
                        END
                        WHERE election_date = ?
                          AND vuid IN (
                            SELECT ve.vuid FROM voter_elections ve
                            JOIN voters v ON ve.vuid = v.vuid
                            WHERE v.county = ? AND ve.election_date = ?
                          )
                    """, [election_date, county, election_date, county, election_date]).rowcount
                    
                else:
                    print(f"  ⚠ Limited history - applying Rule 1 only (newly eligible voters)")
                    
                    # Rule 1: Only mark as new if voter was under 18 for all prior elections
                    # Get earliest prior election
                    earliest = conn.execute("""
                        SELECT MIN(election_date) FROM voter_elections
                        WHERE election_date < ?
                          AND party_voted != '' AND party_voted IS NOT NULL
                    """, [election_date]).fetchone()[0]
                    
                    if earliest:
                        earliest_year = int(earliest.split('-')[0])
                        
                        updated = conn.execute("""
                            UPDATE voter_elections
                            SET is_new_voter = CASE
                                WHEN EXISTS (
                                    SELECT 1 FROM voter_elections ve2
                                    WHERE ve2.vuid = voter_elections.vuid
                                      AND ve2.election_date < ?
                                      AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL
                                ) THEN 0
                                WHEN vuid IN (
                                    SELECT v.vuid FROM voters v
                                    WHERE v.county = ?
                                      AND v.birth_year IS NOT NULL
                                      AND (? - v.birth_year) < 18
                                ) THEN 1
                                ELSE 0
                            END
                            WHERE election_date = ?
                              AND vuid IN (
                                SELECT ve.vuid FROM voter_elections ve
                                JOIN voters v ON ve.vuid = v.vuid
                                WHERE v.county = ? AND ve.election_date = ?
                              )
                        """, [election_date, county, earliest_year, election_date, county, election_date]).rowcount
                    else:
                        # No prior elections - set all to 0
                        updated = conn.execute("""
                            UPDATE voter_elections
                            SET is_new_voter = 0
                            WHERE election_date = ?
                              AND vuid IN (
                                SELECT ve.vuid FROM voter_elections ve
                                JOIN voters v ON ve.vuid = v.vuid
                                WHERE v.county = ? AND ve.election_date = ?
                              )
                        """, [election_date, county, election_date]).rowcount
                
                # Count new voters after update
                new_count = conn.execute("""
                    SELECT COUNT(*)
                    FROM voter_elections ve
                    JOIN voters v ON ve.vuid = v.vuid
                    WHERE v.county = ? AND ve.election_date = ?
                      AND ve.is_new_voter = 1
                """, [county, election_date]).fetchone()[0]
                
                print(f"  Updated {updated:,} records")
                print(f"  New voters: {new_count:,} ({new_count/voter_count*100:.1f}%)")
        
        conn.commit()
        
        print(f"\n{'='*80}")
        print("SUMMARY")
        print(f"{'='*80}")
        
        # Show totals for 2026-03-03
        target = '2026-03-03'
        total = conn.execute("""
            SELECT COUNT(*) FROM voter_elections
            WHERE election_date = ?
        """, [target]).fetchone()[0]
        
        new_total = conn.execute("""
            SELECT COUNT(*) FROM voter_elections
            WHERE election_date = ? AND is_new_voter = 1
        """, [target]).fetchone()[0]
        
        print(f"\n{target} Primary:")
        print(f"  Total voters: {total:,}")
        print(f"  First-time voters: {new_total:,} ({new_total/total*100:.1f}%)")
        
        # By party
        dem_new = conn.execute("""
            SELECT COUNT(*) FROM voter_elections
            WHERE election_date = ? AND is_new_voter = 1
              AND party_voted = 'Democratic'
        """, [target]).fetchone()[0]
        
        rep_new = conn.execute("""
            SELECT COUNT(*) FROM voter_elections
            WHERE election_date = ? AND is_new_voter = 1
              AND party_voted = 'Republican'
        """, [target]).fetchone()[0]
        
        print(f"  Democratic: {dem_new:,}")
        print(f"  Republican: {rep_new:,}")
        
        print("\n✓ Done! All is_new_voter flags have been recalculated.")
        print("\nNext steps:")
        print("  1. Regenerate district cache: python3 deploy/cache_districts_only.py")
        print("  2. Regenerate county reports: python3 deploy/regenerate_county_report_cache.py")
        print("  3. Regenerate gazette cache: python3 deploy/generate_statewide_gazette_cache.py")

if __name__ == '__main__':
    fix_new_voter_flags()
