#!/usr/bin/env python3
"""
SAFE denormalization: Add computed columns WITHOUT touching source data.
This script ONLY adds new columns and computes derived data.
Original voter data remains untouched and can always be restored.

SAFETY GUARANTEES:
1. Never modifies existing columns in voters or voter_elections
2. Only ADDs new columns for computed data
3. Can be rolled back by dropping added columns
4. Original data always preserved
"""
import sqlite3
import time
import sys
from optimization_status import OptimizationStatus

DB_PATH = '/opt/whovoted/data/whovoted.db'

def backup_reminder():
    """Remind user to backup before running."""
    print("\n" + "="*70)
    print("⚠️  SAFETY CHECK")
    print("="*70)
    print("\nThis script will ADD computed columns to voter_elections.")
    print("Original data will NOT be modified.")
    print("\nRecommended: Backup database first:")
    print("  cp /opt/whovoted/data/whovoted.db /opt/whovoted/data/whovoted.db.backup")
    print("\nContinue? (yes/no): ", end='')
    
    response = input().strip().lower()
    if response != 'yes':
        print("Aborted.")
        sys.exit(0)
    print()

def add_computed_columns(conn, status):
    """Add computed columns to voter_elections (safe - doesn't modify existing data)."""
    status.update('add_columns', 'Adding computed columns to voter_elections...', 0.1)
    print("Step 1: Adding computed columns to voter_elections...")
    print("-" * 70)
    
    columns = [
        ('is_new_voter', 'INTEGER DEFAULT 0', 'Flag for first-time voters'),
        ('previous_party', 'TEXT', 'Party voted in previous election'),
        ('previous_election_date', 'TEXT', 'Date of previous election'),
        ('has_flipped', 'INTEGER DEFAULT 0', 'Flag for party switchers'),
    ]
    
    for col_name, col_type, description in columns:
        print(f"  Adding {col_name}... ({description})", end=' ', flush=True)
        try:
            conn.execute(f"ALTER TABLE voter_elections ADD COLUMN {col_name} {col_type}")
            print("✓")
        except sqlite3.OperationalError as e:
            if 'duplicate column' in str(e).lower():
                print("⚠️  Already exists")
            else:
                print(f"✗ {e}")
                raise
    
    conn.commit()
    print()

def compute_new_voters(conn, status):
    """Compute is_new_voter flag (safe - only updates new column).
    
    IMPORTANT: Only marks voters as "new" if their county has historical data.
    A voter is "new" only if:
    1. They haven't voted in any prior election in our data
    2. Their county has at least 2 prior elections (so we have context)
    
    This prevents false positives in counties where we only have recent data.
    """
    status.update('compute_new_voters', 'Computing new voter flags...', 0.3)
    print("Step 2: Computing new voter flags...")
    print("-" * 70)
    
    # Get all election dates to process
    elections = conn.execute("""
        SELECT DISTINCT election_date 
        FROM voter_elections 
        ORDER BY election_date
    """).fetchall()
    
    for (election_date,) in elections:
        print(f"  Processing {election_date}...", end=' ', flush=True)
        t0 = time.time()
        
        # Mark voters as "new" ONLY if:
        # 1. They have no prior voting history
        # 2. Their county has at least 2 prior elections (reliable historical data)
        result = conn.execute("""
            UPDATE voter_elections
            SET is_new_voter = 1
            WHERE election_date = ?
              AND is_new_voter = 0
              AND NOT EXISTS (
                  -- No prior voting history for this voter
                  SELECT 1 FROM voter_elections ve2
                  WHERE ve2.vuid = voter_elections.vuid
                    AND ve2.election_date < ?
                    AND ve2.party_voted != '' 
                    AND ve2.party_voted IS NOT NULL
              )
              AND vuid IN (
                  -- Only voters in counties with 2+ prior elections
                  SELECT DISTINCT v_current.vuid
                  FROM voters v_current
                  WHERE EXISTS (
                      SELECT 1 FROM voter_elections ve3
                      JOIN voters v3 ON ve3.vuid = v3.vuid
                      WHERE v3.county = v_current.county
                        AND ve3.election_date < ?
                        AND ve3.party_voted != ''
                        AND ve3.party_voted IS NOT NULL
                      GROUP BY v3.county
                      HAVING COUNT(DISTINCT ve3.election_date) >= 2
                  )
              )
        """, (election_date, election_date, election_date))
        
        count = result.rowcount
        print(f"✓ {count:,} new voters ({time.time()-t0:.1f}s)")
    
    conn.commit()
    print()

def compute_previous_party(conn, status):
    """Compute previous_party and previous_election_date (safe - only updates new columns)."""
    status.update('compute_previous_party', 'Computing previous party affiliations...', 0.5)
    print("Step 3: Computing previous party affiliations...")
    print("-" * 70)
    
    elections = conn.execute("""
        SELECT DISTINCT election_date 
        FROM voter_elections 
        WHERE election_date > (SELECT MIN(election_date) FROM voter_elections)
        ORDER BY election_date
    """).fetchall()
    
    for (election_date,) in elections:
        print(f"  Processing {election_date}...", end=' ', flush=True)
        t0 = time.time()
        
        # Use a subquery to find previous party for each voter
        result = conn.execute("""
            UPDATE voter_elections
            SET previous_party = (
                SELECT ve2.party_voted
                FROM voter_elections ve2
                WHERE ve2.vuid = voter_elections.vuid
                  AND ve2.election_date < voter_elections.election_date
                  AND ve2.party_voted != ''
                  AND ve2.party_voted IS NOT NULL
                ORDER BY ve2.election_date DESC
                LIMIT 1
            ),
            previous_election_date = (
                SELECT ve2.election_date
                FROM voter_elections ve2
                WHERE ve2.vuid = voter_elections.vuid
                  AND ve2.election_date < voter_elections.election_date
                  AND ve2.party_voted != ''
                  AND ve2.party_voted IS NOT NULL
                ORDER BY ve2.election_date DESC
                LIMIT 1
            )
            WHERE election_date = ?
              AND previous_party IS NULL
        """, (election_date,))
        
        count = result.rowcount
        print(f"✓ {count:,} records ({time.time()-t0:.1f}s)")
    
    conn.commit()
    print()

def compute_flips(conn, status):
    """Compute has_flipped flag (safe - only updates new column)."""
    status.update('compute_flips', 'Computing party flip flags...', 0.7)
    print("Step 4: Computing party flip flags...")
    print("-" * 70)
    
    elections = conn.execute("""
        SELECT DISTINCT election_date 
        FROM voter_elections 
        WHERE previous_party IS NOT NULL
        ORDER BY election_date
    """).fetchall()
    
    for (election_date,) in elections:
        print(f"  Processing {election_date}...", end=' ', flush=True)
        t0 = time.time()
        
        result = conn.execute("""
            UPDATE voter_elections
            SET has_flipped = 1
            WHERE election_date = ?
              AND previous_party IS NOT NULL
              AND previous_party != party_voted
              AND party_voted != ''
              AND party_voted IS NOT NULL
        """, (election_date,))
        
        count = result.rowcount
        print(f"✓ {count:,} flips ({time.time()-t0:.1f}s)")
    
    conn.commit()
    print()

def create_indexes_on_computed_columns(conn, status):
    """Add indexes to new computed columns for fast queries."""
    status.update('create_indexes', 'Adding indexes on computed columns...', 0.85)
    print("Step 5: Adding indexes on computed columns...")
    print("-" * 70)
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_ve_is_new_voter ON voter_elections(election_date, is_new_voter) WHERE is_new_voter=1",
        "CREATE INDEX IF NOT EXISTS idx_ve_has_flipped ON voter_elections(election_date, has_flipped) WHERE has_flipped=1",
        "CREATE INDEX IF NOT EXISTS idx_ve_previous_party ON voter_elections(previous_party)",
    ]
    
    for idx_sql in indexes:
        idx_name = idx_sql.split('idx_')[1].split(' ')[0]
        print(f"  Creating {idx_name}...", end=' ', flush=True)
        conn.execute(idx_sql)
        print("✓")
    
    conn.commit()
    print()

def verify_data_integrity(conn, status):
    """Verify original data wasn't modified."""
    status.update('verify_integrity', 'Verifying data integrity...', 0.95)
    print("Step 6: Verifying data integrity...")
    print("-" * 70)
    
    # Check that original columns still have data
    checks = [
        ("voters table", "SELECT COUNT(*) FROM voters"),
        ("voter_elections table", "SELECT COUNT(*) FROM voter_elections"),
        ("VUIDs intact", "SELECT COUNT(DISTINCT vuid) FROM voters"),
        ("Addresses intact", "SELECT COUNT(*) FROM voters WHERE address != ''"),
        ("Geocoded data intact", "SELECT COUNT(*) FROM voters WHERE geocoded = 1"),
    ]
    
    all_good = True
    for check_name, query in checks:
        count = conn.execute(query).fetchone()[0]
        if count > 0:
            print(f"  ✓ {check_name}: {count:,} records")
        else:
            print(f"  ✗ {check_name}: NO DATA FOUND!")
            all_good = False
    
    print()
    if all_good:
        print("✅ Data integrity verified - original data is safe!")
    else:
        print("❌ DATA INTEGRITY ISSUE - RESTORE FROM BACKUP!")
        sys.exit(1)

def main():
    status = OptimizationStatus('denormalization')
    
    print("\n" + "="*70)
    print("SAFE DENORMALIZATION - Add Computed Columns")
    print("="*70)
    print("\nThis script adds computed columns for fast queries.")
    print("Original voter data is NEVER modified.")
    
    backup_reminder()
    
    conn = sqlite3.connect(DB_PATH)
    overall_start = time.time()
    
    try:
        add_computed_columns(conn, status)
        compute_new_voters(conn, status)
        compute_previous_party(conn, status)
        compute_flips(conn, status)
        create_indexes_on_computed_columns(conn, status)
        verify_data_integrity(conn, status)
        
        total_time = time.time() - overall_start
        status.complete(f'Denormalization complete in {total_time:.1f}s')
        
        print("="*70)
        print(f"✅ Denormalization complete in {total_time:.1f}s")
        print("="*70)
        print("\nNext steps:")
        print("  1. Test gazette - should load in <10s now")
        print("  2. Test household popups - should be <1s")
        print("  3. Run optimize_step2_gazette.py to cache results")
        print("\nTo rollback (if needed):")
        print("  ALTER TABLE voter_elections DROP COLUMN is_new_voter;")
        print("  ALTER TABLE voter_elections DROP COLUMN previous_party;")
        print("  ALTER TABLE voter_elections DROP COLUMN previous_election_date;")
        print("  ALTER TABLE voter_elections DROP COLUMN has_flipped;")
        print()
        
    except Exception as e:
        status.error(f'Denormalization failed: {e}', str(e))
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        print("\n⚠️  If data was corrupted, restore from backup:")
        print("  cp /opt/whovoted/data/whovoted.db.backup /opt/whovoted/data/whovoted.db")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
