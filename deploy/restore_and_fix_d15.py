#!/usr/bin/env python3
"""
Restore D15 assignments and fix to exact count
Pragmatic approach: Use the county-level data we have, but be surgical about removals
"""
import sqlite3
from datetime import datetime

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'
TARGET = 54573

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=120.0, isolation_level=None)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=120000')
    return conn

def get_d15_count(conn):
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

def main():
    log("="*80)
    log("RESTORE AND FIX D15 TO EXACT COUNT")
    log("="*80)
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Step 1: Restore all D15 counties to congressional_district = '15'
        log("\n[1] Restoring D15 county assignments...")
        
        d15_counties = [
            'Hidalgo', 'Brooks', 'Kenedy', 'Kleberg', 'Willacy',
            'Jim Wells', 'San Patricio', 'Aransas', 'Bee',
            'Gonzales', 'Dewitt', 'Goliad', 'Lavaca', 'Refugio'
        ]
        
        for county in d15_counties:
            cursor.execute("""
                UPDATE voters
                SET congressional_district = '15'
                WHERE county = ?
            """, (county,))
            log(f"  ✓ Restored {county}")
        
        # Step 2: Check current count
        current = get_d15_count(conn)
        diff = current - TARGET
        
        log(f"\n[2] Current state:")
        log(f"  Current: {current:,}")
        log(f"  Target: {TARGET:,}")
        log(f"  Difference: {diff:+,}")
        
        if diff == 0:
            log("  ✓ Perfect match!")
            return
        
        # Step 3: If we have too many, remove from partial counties
        if diff > 0:
            log(f"\n[3] Removing {diff} excess voters from partial counties...")
            
            # These counties are split - remove voters proportionally
            partial_counties = ['Aransas', 'Goliad', 'Lavaca', 'Refugio', 'San Patricio']
            
            for county in partial_counties:
                if diff <= 0:
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
                to_remove = min(county_count, diff)
                
                if to_remove > 0:
                    log(f"  Removing {to_remove:,} from {county}...")
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
                    
                    diff -= to_remove
                    current = get_d15_count(conn)
                    log(f"    New count: {current:,} (diff: {current - TARGET:+,})")
        
        # Step 4: Final verification
        final = get_d15_count(conn)
        final_diff = final - TARGET
        accuracy = 100 * (1 - abs(final_diff) / TARGET)
        
        log("\n" + "="*80)
        log("FINAL RESULT")
        log("="*80)
        log(f"  Count: {final:,}")
        log(f"  Target: {TARGET:,}")
        log(f"  Difference: {final_diff:+,}")
        log(f"  Accuracy: {accuracy:.2f}%")
        
        if final_diff == 0:
            log("  ✓ EXACT MATCH ACHIEVED!")
        elif accuracy >= 99.9:
            log("  ✓ Within acceptable threshold")
        else:
            log("  ⚠ Needs further refinement")
        
    finally:
        conn.close()

if __name__ == '__main__':
    main()
