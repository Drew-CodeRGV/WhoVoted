#!/usr/bin/env python3
"""
Step 1: Add critical database indexes.
This is safe to run anytime and will dramatically speed up queries.
Run time: ~30 seconds
"""
import sqlite3
import sys
import time
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'

def main():
    print("\n" + "="*70)
    print("STEP 1: Adding Database Indexes")
    print("="*70)
    
    if not Path(DB_PATH).exists():
        print(f"❌ Database not found: {DB_PATH}")
        sys.exit(1)
    
    conn = sqlite3.connect(DB_PATH)
    
    # Define indexes with descriptions
    indexes = [
        {
            'name': 'idx_voters_coords',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_voters_coords ON voters(lat, lng) WHERE geocoded=1',
            'purpose': 'Fast household popup lookups by coordinates'
        },
        {
            'name': 'idx_voters_address',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_voters_address ON voters(address)',
            'purpose': 'Fast address matching for households'
        },
        {
            'name': 'idx_voters_county_geocoded',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_voters_county_geocoded ON voters(county, geocoded)',
            'purpose': 'Fast county filtering'
        },
        {
            'name': 'idx_ve_vuid_date_party',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_ve_vuid_date_party ON voter_elections(vuid, election_date, party_voted)',
            'purpose': 'Fast voter history lookups (flips, new voters)'
        },
        {
            'name': 'idx_ve_election_party',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_ve_election_party ON voter_elections(election_date, party_voted)',
            'purpose': 'Fast party filtering by election'
        },
        {
            'name': 'idx_ve_date_method',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_ve_date_method ON voter_elections(election_date, voting_method)',
            'purpose': 'Fast voting method filtering'
        },
        {
            'name': 'idx_voters_sex',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_voters_sex ON voters(sex)',
            'purpose': 'Fast gender filtering'
        },
        {
            'name': 'idx_voters_birth_year',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_voters_birth_year ON voters(birth_year)',
            'purpose': 'Fast age filtering'
        },
        {
            'name': 'idx_voters_county',
            'sql': 'CREATE INDEX IF NOT EXISTS idx_voters_county ON voters(county)',
            'purpose': 'Fast county lookups'
        },
    ]
    
    print(f"\nCreating {len(indexes)} indexes...\n")
    
    total_start = time.time()
    created = 0
    
    for idx in indexes:
        print(f"  {idx['name']:<30} ", end='', flush=True)
        print(f"({idx['purpose']})", end=' ', flush=True)
        
        t0 = time.time()
        try:
            conn.execute(idx['sql'])
            elapsed = time.time() - t0
            print(f"✓ {elapsed:.1f}s")
            created += 1
        except Exception as e:
            print(f"✗ {e}")
    
    conn.commit()
    
    print(f"\n✅ Created {created}/{len(indexes)} indexes")
    
    # Run ANALYZE to update query planner statistics
    print("\nUpdating query planner statistics (ANALYZE)...", end=' ', flush=True)
    try:
        conn.execute("ANALYZE")
        conn.commit()
        print("✓")
    except sqlite3.OperationalError as e:
        if 'locked' in str(e):
            print("⚠️  Database locked (app is running)")
            print("   Indexes are created, but ANALYZE will run on next app restart")
        else:
            print(f"✗ {e}")
    
    conn.close()
    
    total_time = time.time() - total_start
    print(f"\n{'='*70}")
    print(f"✅ Optimization complete in {total_time:.1f}s")
    print(f"{'='*70}\n")
    
    print("Next steps:")
    print("  1. Test household popup - should be <1s now")
    print("  2. Restart app to run ANALYZE: sudo supervisorctl restart whovoted")
    print("  3. Run Step 2 to pre-compute gazette data\n")

if __name__ == '__main__':
    main()
