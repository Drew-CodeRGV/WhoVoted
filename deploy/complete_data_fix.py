#!/usr/bin/env python3
"""
Complete fix for voter data:
1. Delete all 2026-03-03 data
2. Re-import from EVR scraper
3. Re-import from Election Day scraper
4. Fix district assignments using precinct data only
5. Verify counts
"""
import sqlite3
import sys

DB_PATH = '/opt/whovoted/data/whovoted.db'

def main():
    conn = sqlite3.connect(DB_PATH, timeout=60.0)
    cursor = conn.cursor()
    
    print("="*80)
    print("COMPLETE VOTER DATA FIX")
    print("="*80)
    
    # Step 1: Check current state
    print("\n[1/5] Checking current state...")
    cursor.execute("""
        SELECT 
            COUNT(*) as total_records,
            COUNT(DISTINCT vuid) as unique_voters
        FROM voter_elections
        WHERE election_date = '2026-03-03'
    """)
    total_records, unique_voters = cursor.fetchone()
    print(f"  Current: {total_records:,} records, {unique_voters:,} unique voters")
    
    # Step 2: Delete all 2026-03-03 data
    print("\n[2/5] Deleting all 2026-03-03 election data...")
    cursor.execute("DELETE FROM voter_elections WHERE election_date = '2026-03-03'")
    deleted = cursor.rowcount
    print(f"  Deleted: {deleted:,} records")
    conn.commit()
    
    # Step 3: Verify deletion
    cursor.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = '2026-03-03'")
    remaining = cursor.fetchone()[0]
    if remaining > 0:
        print(f"  ✗ ERROR: {remaining:,} records still remain!")
        return False
    print(f"  ✓ All 2026-03-03 data deleted")
    
    # Step 4: Instructions for re-import
    print("\n[3/5] Data cleared. Ready for re-import.")
    print("\nNext steps:")
    print("  1. Run EVR scraper to import early voting data")
    print("  2. Run Election Day scraper to import election day data")
    print("  3. Run district assignment with precinct-only mode")
    print("  4. Verify counts match official numbers")
    
    conn.close()
    
    print("\n" + "="*80)
    print("STEP 1 COMPLETE - Data cleared")
    print("="*80)
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
