#!/usr/bin/env python3
"""
Add district columns to voters table for instant lookups.

This adds denormalized columns to the voters table:
- congressional_district
- state_house_district  
- commissioner_district

These are populated based on the precinct-to-district mapping,
enabling instant district queries without point-in-polygon checks.
"""

import json
import sqlite3
import time
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
MAPPING_FILE = '/opt/whovoted/public/cache/precinct_district_mapping.json'

def normalize_precinct_for_lookup(precinct):
    """Normalize precinct ID for database lookup."""
    if not precinct:
        return []
    
    p = str(precinct).strip()
    
    # Generate all possible variations
    variations = [p]
    
    # Remove common prefixes/suffixes
    cleaned = p.replace('S ', '').replace('.', '').strip()
    if cleaned != p:
        variations.append(cleaned)
    
    # If numeric, add zero-padded versions
    if cleaned.isdigit():
        num = int(cleaned)
        variations.extend([
            str(num),  # No padding
            f"{num:02d}",  # 2 digits
            f"{num:03d}",  # 3 digits
            f"{num:04d}",  # 4 digits
        ])
    
    return list(set(variations))

def main():
    print("=" * 70)
    print("Adding District Columns to Voters Table")
    print("=" * 70)
    
    # Load mapping
    print("\n1. Loading precinct-to-district mapping...")
    with open(MAPPING_FILE) as f:
        mapping = json.load(f)
    
    # Build reverse lookup: precinct_id -> districts
    print("2. Building reverse lookup (precinct -> districts)...")
    precinct_to_districts = {}
    
    for district_name, data in mapping.items():
        district_type = data['district_type']
        district_id = data['district_id']
        
        for precinct_id in data['precincts']:
            # Generate all variations of this precinct ID
            variations = normalize_precinct_for_lookup(precinct_id)
            
            for var in variations:
                if var not in precinct_to_districts:
                    precinct_to_districts[var] = {
                        'congressional': None,
                        'state_house': None,
                        'commissioner': None
                    }
                
                if district_type == 'congressional':
                    precinct_to_districts[var]['congressional'] = district_id
                elif district_type == 'state_house':
                    precinct_to_districts[var]['state_house'] = district_id
                elif district_type == 'commissioner':
                    precinct_to_districts[var]['commissioner'] = district_id
    
    print(f"   Built lookup for {len(precinct_to_districts)} precinct variations")
    
    # Connect to database
    print("\n3. Connecting to database...")
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Add columns if they don't exist
    print("4. Adding district columns to voters table...")
    try:
        conn.execute("ALTER TABLE voters ADD COLUMN congressional_district TEXT")
        print("   ✓ Added congressional_district column")
    except:
        print("   - congressional_district column already exists")
    
    try:
        conn.execute("ALTER TABLE voters ADD COLUMN state_house_district TEXT")
        print("   ✓ Added state_house_district column")
    except:
        print("   - state_house_district column already exists")
    
    try:
        conn.execute("ALTER TABLE voters ADD COLUMN commissioner_district TEXT")
        print("   ✓ Added commissioner_district column")
    except:
        print("   - commissioner_district column already exists")
    
    conn.commit()
    
    # Update voters with district assignments
    print("\n5. Updating voter district assignments...")
    print("   This may take a few minutes...")
    
    start_time = time.time()
    updated = 0
    not_found = 0
    
    # Get all voters with precincts
    voters = conn.execute("""
        SELECT vuid, precinct 
        FROM voters 
        WHERE precinct IS NOT NULL AND precinct != ''
    """).fetchall()
    
    total = len(voters)
    print(f"   Processing {total:,} voters...")
    
    batch = []
    for i, voter in enumerate(voters):
        vuid = voter['vuid']
        precinct = voter['precinct']
        
        # Look up districts for this precinct
        districts = precinct_to_districts.get(precinct)
        
        if districts:
            batch.append((
                districts['congressional'],
                districts['state_house'],
                districts['commissioner'],
                vuid
            ))
            updated += 1
        else:
            not_found += 1
        
        # Batch update every 10,000 records
        if len(batch) >= 10000:
            conn.executemany("""
                UPDATE voters 
                SET congressional_district = ?,
                    state_house_district = ?,
                    commissioner_district = ?
                WHERE vuid = ?
            """, batch)
            conn.commit()
            batch = []
            
            if (i + 1) % 50000 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1) / elapsed
                remaining = (total - i - 1) / rate
                print(f"   Progress: {i+1:,}/{total:,} ({(i+1)*100/total:.1f}%) - "
                      f"{rate:.0f} voters/sec - ETA: {remaining:.0f}s")
    
    # Final batch
    if batch:
        conn.executemany("""
            UPDATE voters 
            SET congressional_district = ?,
                state_house_district = ?,
                commissioner_district = ?
            WHERE vuid = ?
        """, batch)
        conn.commit()
    
    elapsed = time.time() - start_time
    
    # Create indexes
    print("\n6. Creating indexes on district columns...")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_voters_congressional ON voters(congressional_district)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_voters_state_house ON voters(state_house_district)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_voters_commissioner ON voters(commissioner_district)")
    conn.commit()
    print("   ✓ Indexes created")
    
    # Show statistics
    print("\n7. Statistics:")
    print(f"   Total voters processed: {total:,}")
    print(f"   Voters assigned to districts: {updated:,} ({updated*100/total:.1f}%)")
    print(f"   Voters not mapped: {not_found:,} ({not_found*100/total:.1f}%)")
    print(f"   Time elapsed: {elapsed:.1f} seconds")
    print(f"   Rate: {total/elapsed:.0f} voters/second")
    
    # Show district counts
    print("\n8. Voters per district:")
    
    for district_type, column in [
        ('Congressional', 'congressional_district'),
        ('State House', 'state_house_district'),
        ('Commissioner', 'commissioner_district')
    ]:
        print(f"\n   {district_type}:")
        rows = conn.execute(f"""
            SELECT {column}, COUNT(*) as cnt
            FROM voters
            WHERE {column} IS NOT NULL
            GROUP BY {column}
            ORDER BY cnt DESC
        """).fetchall()
        
        for row in rows:
            print(f"      {row[0]:30s} {row[1]:8,d} voters")
    
    conn.close()
    
    print("\n" + "=" * 70)
    print("✅ District Columns Added Successfully!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Update backend to use district columns for queries")
    print("2. Regenerate district cache files")
    print("3. Test district reports for accuracy and speed")

if __name__ == '__main__':
    main()
