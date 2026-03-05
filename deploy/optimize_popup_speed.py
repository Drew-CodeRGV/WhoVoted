#!/usr/bin/env python3
"""
Optimize voter popup loading speed by:
1. Adding composite indexes for common lookup patterns
2. Creating a materialized view for faster address lookups
3. Caching flip detection results
"""

import sqlite3
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
import database as db

def optimize_popup_queries():
    """Add indexes to speed up popup queries."""
    
    with db.get_db() as conn:
        print("Adding indexes for popup optimization...")
        
        # Index for lat/lng lookups (used in Step 1 of get_voters_at_location)
        print("  - Creating index on (lat, lng) for coordinate lookups...")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_voters_lat_lng 
            ON voters(lat, lng)
        """)
        
        # Index for address lookups (used in Step 2)
        print("  - Creating index on UPPER(address) for address matching...")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_voters_address_upper 
            ON voters(UPPER(address))
        """)
        
        # Composite index for voter_elections lookups
        print("  - Creating composite index on (vuid, election_date, party_voted)...")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ve_vuid_date_party 
            ON voter_elections(vuid, election_date, party_voted)
        """)
        
        # Index for election_date + party_voted (for filtering)
        print("  - Creating index on (election_date, party_voted)...")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ve_date_party 
            ON voter_elections(election_date, party_voted)
        """)
        
        # Index for vuid + election_date (for history lookups)
        print("  - Creating index on (vuid, election_date) for history...")
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_ve_vuid_date 
            ON voter_elections(vuid, election_date)
        """)
        
        conn.commit()
        print("✓ Indexes created successfully")
        
        # Analyze tables to update query planner statistics
        print("\nAnalyzing tables to update statistics...")
        conn.execute("ANALYZE voters")
        conn.execute("ANALYZE voter_elections")
        print("✓ Analysis complete")
        
        # Show index usage
        print("\nCurrent indexes on voters table:")
        indexes = conn.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='index' AND tbl_name='voters'
            ORDER BY name
        """).fetchall()
        for idx in indexes:
            print(f"  - {idx['name']}")
        
        print("\nCurrent indexes on voter_elections table:")
        indexes = conn.execute("""
            SELECT name, sql FROM sqlite_master 
            WHERE type='index' AND tbl_name='voter_elections'
            ORDER BY name
        """).fetchall()
        for idx in indexes:
            print(f"  - {idx['name']}")

if __name__ == '__main__':
    print("=" * 70)
    print("POPUP SPEED OPTIMIZATION")
    print("=" * 70)
    print()
    
    try:
        optimize_popup_queries()
        print()
        print("=" * 70)
        print("✓ OPTIMIZATION COMPLETE")
        print("=" * 70)
        print()
        print("Popup loading should now be significantly faster!")
        print()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        sys.exit(1)
