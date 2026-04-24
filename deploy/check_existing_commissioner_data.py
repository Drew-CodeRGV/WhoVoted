#!/usr/bin/env python3
"""
Check if voters already have commissioner district assignments in the database.
"""

import sqlite3

DB_PATH = '/opt/whovoted/data/whovoted.db'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("="*80)
print("CHECKING FOR EXISTING COMMISSIONER DISTRICT DATA")
print("="*80)

# Check table schema
cur.execute("PRAGMA table_info(voters)")
columns = [row['name'] for row in cur.fetchall()]
print(f"\nColumns in voters table:")
for col in columns:
    print(f"  {col}")

# Check if there's a commissioner district column
commissioner_cols = [c for c in columns if 'commissioner' in c.lower()]
if commissioner_cols:
    print(f"\n✓ Found commissioner columns: {commissioner_cols}")
    
    for col in commissioner_cols:
        # Check how many voters have this data
        cur.execute(f"SELECT COUNT(*) FROM voters WHERE {col} IS NOT NULL AND {col} != ''")
        count = cur.fetchone()[0]
        
        cur.execute(f"SELECT COUNT(*) FROM voters WHERE county = 'Hidalgo'")
        total_hidalgo = cur.fetchone()[0]
        
        print(f"\n{col}:")
        print(f"  Total with data: {count:,}")
        print(f"  Hidalgo voters: {total_hidalgo:,}")
        
        # Check unique values
        cur.execute(f"SELECT DISTINCT {col}, COUNT(*) as cnt FROM voters WHERE county = 'Hidalgo' AND {col} IS NOT NULL GROUP BY {col} ORDER BY {col}")
        print(f"  Unique values in Hidalgo:")
        for row in cur.fetchall():
            print(f"    {row[0]}: {row[1]:,} voters")
        
        # If we have commissioner data, use it to count votes
        if count > 0:
            print(f"\n  Calculating vote counts using {col}...")
            
            cur.execute(f"""
                SELECT 
                    v.{col} as cpct,
                    COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'early-voting' THEN ve.vuid END) as dem_early,
                    COUNT(DISTINCT CASE WHEN ve.party_voted IN ('DEM','D','Democratic') AND ve.voting_method = 'election-day' THEN ve.vuid END) as dem_eday,
                    COUNT(DISTINCT CASE WHEN ve.party_voted IN ('REP','R','Republican') THEN ve.vuid END) as rep_total
                FROM voters v
                INNER JOIN voter_elections ve ON v.vuid = ve.vuid
                WHERE v.county = 'Hidalgo' AND v.{col} IS NOT NULL
                AND ve.election_date = '2026-03-03'
                AND ve.data_source = 'county-upload'
                GROUP BY v.{col}
                ORDER BY v.{col}
            """)
            
            print(f"\n  Vote counts by {col}:")
            print(f"  {'District':<12} {'DEM Early':>12} {'DEM EDay':>12} {'DEM Total':>12} {'REP Total':>12}")
            print("  " + "-"*60)
            
            for row in cur.fetchall():
                cpct = row['cpct']
                dem_early = row['dem_early']
                dem_eday = row['dem_eday']
                dem_total = dem_early + dem_eday
                rep_total = row['rep_total']
                
                print(f"  {cpct:<12} {dem_early:>12,} {dem_eday:>12,} {dem_total:>12,} {rep_total:>12,}")
                
                if cpct == '2' or cpct == 2:
                    print(f"\n  CPct-2 Results:")
                    print(f"    DEM Early: {dem_early:,} (certified: 9,876, diff: {abs(dem_early-9876)})")
                    print(f"    DEM EDay: {dem_eday:,} (certified: 3,754, diff: {abs(dem_eday-3754)})")
                    print(f"    DEM Total: {dem_total:,} (certified: 13,630, diff: {abs(dem_total-13630)})")
else:
    print("\n✗ No commissioner district columns found")
    print("\nWe need to either:")
    print("1. Get the precinct-to-commissioner mapping from the county")
    print("2. Use the boundary polygons to map precincts")
    print("3. Accept the current boundary and note the discrepancy")

conn.close()
