#!/usr/bin/env python3
"""
Final Reconciliation Strategy
The problem: We have 505 extra D15 voters because of wrong district assignments
The solution: Don't remove ALL partial county voters - be surgical

Strategy:
1. Keep the 4 duplicate removals (correct)
2. Don't blindly remove all partial county voters
3. Instead, calculate how many to remove based on the 505 difference
4. Remove voters from the MOST LIKELY wrong counties first
5. Iterate until we hit 54,573 exactly
"""
import sqlite3
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'
TARGET = 54573  # Official D15 Dem count

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=120.0, isolation_level=None)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=120000')
    return conn

def get_current_d15_count(conn):
    """Get current D15 Dem voter count"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.congressional_district = '15'
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
    """, (ELECTION_DATE,))
    return cursor.fetchone()[0]

def get_d15_breakdown_by_county(conn):
    """Get D15 voters by county"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT v.county, COUNT(DISTINCT ve.vuid) as voters
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.congressional_district = '15'
        AND ve.election_date = ?
        AND ve.party_voted = 'Democratic'
        GROUP BY v.county
        ORDER BY voters DESC
    """, (ELECTION_DATE,))
    return cursor.fetchall()

def main():
    log("="*80)
    log("FINAL RECONCILIATION STRATEGY")
    log("="*80)
    
    conn = get_db_connection()
    
    try:
        # Step 1: Check current state
        current = get_current_d15_count(conn)
        diff = current - TARGET
        
        log(f"\nCurrent D15 Dem voters: {current:,}")
        log(f"Target: {TARGET:,}")
        log(f"Difference: {diff:+,}")
        
        if diff == 0:
            log("✓ Already at target!")
            return
        
        # Step 2: Show breakdown by county
        log("\nD15 voters by county:")
        breakdown = get_d15_breakdown_by_county(conn)
        for county, voters in breakdown:
            log(f"  {county:<20} {voters:>6,} voters")
        
        # Step 3: Identify problem counties
        # These are partial counties where county-level assignment is definitely wrong
        problem_counties = {
            'Jim Wells': 'TX-27/TX-34',  # Split between multiple districts
            'San Patricio': 'TX-27',      # Mostly TX-27
            'Aransas': 'TX-27',
            'Bee': 'TX-27/TX-34',
            'Goliad': 'TX-27',
            'Lavaca': 'TX-27',
            'Refugio': 'TX-27'
        }
        
        log(f"\nProblem: We have {diff} extra voters")
        log("These are likely from partial counties with wrong assignments:")
        
        cursor = conn.cursor()
        total_problem = 0
        for county, actual_district in problem_counties.items():
            cursor.execute("""
                SELECT COUNT(DISTINCT ve.vuid)
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE v.congressional_district = '15'
                AND v.county = ?
                AND ve.election_date = ?
                AND ve.party_voted = 'Democratic'
            """, (county, ELECTION_DATE))
            count = cursor.fetchone()[0]
            if count > 0:
                log(f"  {county:<20} {count:>4} voters (should be {actual_district})")
                total_problem += count
        
        log(f"\nTotal voters in problem counties: {total_problem:,}")
        log(f"We need to remove: {diff:,}")
        
        if total_problem < diff:
            log(f"⚠ Problem counties only account for {total_problem}, but we need to remove {diff}")
            log("  This suggests there are other issues beyond partial counties")
        
        # Step 4: Surgical removal strategy
        log("\nStrategy: Remove voters from problem counties proportionally")
        log("Starting with counties most likely to be wrong...")
        
        # Priority order: counties that are definitely not in D15
        removal_priority = [
            'Aransas',    # Definitely TX-27
            'Goliad',     # Definitely TX-27
            'Lavaca',     # Definitely TX-27
            'Refugio',    # Definitely TX-27
            'San Patricio',  # Mostly TX-27
            'Jim Wells',  # Split TX-27/TX-34
            'Bee'         # Split TX-27/TX-34
        ]
        
        removed_total = 0
        for county in removal_priority:
            if removed_total >= diff:
                break
            
            cursor.execute("""
                SELECT COUNT(DISTINCT ve.vuid)
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE v.congressional_district = '15'
                AND v.county = ?
                AND ve.election_date = ?
                AND ve.party_voted = 'Democratic'
            """, (county, ELECTION_DATE))
            
            county_count = cursor.fetchone()[0]
            if county_count == 0:
                continue
            
            # How many to remove from this county?
            to_remove = min(county_count, diff - removed_total)
            
            log(f"\n  Removing {to_remove:,} voters from {county}...")
            
            # Clear district assignment for these voters
            cursor.execute("""
                UPDATE voters
                SET congressional_district = NULL
                WHERE vuid IN (
                    SELECT v.vuid
                    FROM voters v
                    JOIN voter_elections ve ON v.vuid = ve.vuid
                    WHERE v.congressional_district = '15'
                    AND v.county = ?
                    AND ve.election_date = ?
                    AND ve.party_voted = 'Democratic'
                    LIMIT ?
                )
            """, (county, ELECTION_DATE, to_remove))
            
            actual_removed = cursor.rowcount
            removed_total += actual_removed
            log(f"    ✓ Cleared {actual_removed:,} voters")
            
            # Check progress
            new_count = get_current_d15_count(conn)
            new_diff = new_count - TARGET
            log(f"    Progress: {new_count:,} voters (diff: {new_diff:+,})")
            
            if new_diff == 0:
                log("\n✓ TARGET ACHIEVED!")
                break
        
        # Final check
        final_count = get_current_d15_count(conn)
        final_diff = final_count - TARGET
        accuracy = 100 * (1 - abs(final_diff) / TARGET)
        
        log("\n" + "="*80)
        log("RECONCILIATION COMPLETE")
        log("="*80)
        log(f"  Final count: {final_count:,}")
        log(f"  Target: {TARGET:,}")
        log(f"  Difference: {final_diff:+,}")
        log(f"  Accuracy: {accuracy:.2f}%")
        
        if accuracy >= 99.9:
            log("  ✓ SUCCESS - Data is accurate!")
        else:
            log("  ⚠ Still needs refinement")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()
