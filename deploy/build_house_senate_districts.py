#!/usr/bin/env python3
"""
BUILD HOUSE AND SENATE DISTRICT ASSIGNMENTS

This script:
1. Adds state_house_district and state_senate_district columns if needed
2. Assigns House and Senate districts to voters using the same precinct matching system
3. Generates district cache files for the frontend
"""
import sqlite3
import json
import re
from pathlib import Path
from collections import defaultdict

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'
CACHE_DIR = Path('/opt/whovoted/data/district_cache')


class PrecinctNormalizer:
    """Normalize precinct identifiers for matching"""
    
    @staticmethod
    def normalize(precinct, county=None):
        if not precinct:
            return set()
        
        p = str(precinct).strip().upper()
        normalized = set()
        normalized.add(p)
        no_space = p.replace(' ', '')
        normalized.add(no_space)
        
        numbers = re.findall(r'\d+', p)
        if numbers:
            normalized.add(''.join(numbers))
            for num in numbers:
                normalized.add(num)
                normalized.add(num.lstrip('0') or '0')
                normalized.add(num.zfill(4))
        
        for prefix in ['PCT', 'PRECINCT', 'PRE', 'P', 'S', 'E', 'W', 'N']:
            if p.startswith(prefix):
                suffix = p[len(prefix):].strip()
                if suffix:
                    normalized.add(suffix)
                    normalized.update(PrecinctNormalizer.normalize(suffix))
        
        if '.' in p:
            no_decimal = p.replace('.', '')
            normalized.add(no_decimal)
            parts = p.split('.')
            if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                major = parts[0].strip()
                minor = parts[1].strip()
                normalized.add(f"{major}{minor.zfill(2)}")
                normalized.add(f"{major.zfill(2)}{minor.zfill(2)}")
        
        if '-' in p:
            no_hyphen = p.replace('-', '')
            normalized.add(no_hyphen)
            parts = p.split('-')
            if len(parts) == 2:
                normalized.add(f"{parts[0]}{parts[1].zfill(2)}")
        
        if '/' in p:
            no_slash = p.replace('/', '')
            normalized.add(no_slash)
        
        return normalized


def add_district_columns(conn):
    """Add House and Senate district columns if they don't exist"""
    print("\n1. Adding district columns...")
    cursor = conn.cursor()
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(voter_elections)")
    columns = [row[1] for row in cursor.fetchall()]
    
    if 'state_house_district' not in columns:
        cursor.execute("ALTER TABLE voter_elections ADD COLUMN state_house_district TEXT")
        print("✓ Added state_house_district column")
    else:
        print("✓ state_house_district column exists")
    
    if 'state_senate_district' not in columns:
        cursor.execute("ALTER TABLE voter_elections ADD COLUMN state_senate_district TEXT")
        print("✓ Added state_senate_district column")
    else:
        print("✓ state_senate_district column exists")
    
    conn.commit()


def assign_house_districts(conn):
    """Assign State House districts using precinct matching"""
    print("\n2. Assigning State House Districts...")
    cursor = conn.cursor()
    
    # Get all voting records with precincts
    cursor.execute("""
        SELECT 
            ve.id,
            ve.vuid,
            ve.precinct,
            v.county
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ?
        AND ve.precinct IS NOT NULL 
        AND ve.precinct != ''
        AND v.county IS NOT NULL
        AND v.county != ''
    """, (ELECTION_DATE,))
    
    voting_records = cursor.fetchall()
    total_records = len(voting_records)
    print(f"Processing {total_records:,} voting records...")
    
    # Process in batches
    batch_size = 10000
    assigned = 0
    
    for i in range(0, total_records, batch_size):
        batch = voting_records[i:i+batch_size]
        updates = []
        
        for record_id, vuid, precinct, county in batch:
            variants = PrecinctNormalizer.normalize(precinct, county)
            
            district = None
            for variant in variants:
                cursor.execute("""
                    SELECT state_house_district
                    FROM precinct_normalized
                    WHERE county = ? AND normalized_precinct = ?
                    AND state_house_district IS NOT NULL
                    LIMIT 1
                """, (county, variant))
                
                result = cursor.fetchone()
                if result and result[0]:
                    raw_district = result[0]
                    # Normalize format: "15" → "HD-15"
                    if raw_district.isdigit():
                        district = f"HD-{raw_district}"
                    else:
                        district = raw_district
                    break
            
            if district:
                updates.append((district, record_id))
                assigned += 1
        
        if updates:
            cursor.executemany("""
                UPDATE voter_elections 
                SET state_house_district = ?
                WHERE id = ?
            """, updates)
            conn.commit()
        
        if (i + batch_size) % 100000 == 0:
            print(f"  Processed {min(i + batch_size, total_records):,} / {total_records:,} records...")
    
    match_rate = 100 * assigned / total_records if total_records > 0 else 0
    print(f"✓ Assigned {assigned:,} records ({match_rate:.1f}%)")
    
    return assigned


def assign_senate_districts(conn):
    """Assign State Senate districts using precinct matching"""
    print("\n3. Assigning State Senate Districts...")
    cursor = conn.cursor()
    
    # Get all voting records with precincts
    cursor.execute("""
        SELECT 
            ve.id,
            ve.vuid,
            ve.precinct,
            v.county
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ?
        AND ve.precinct IS NOT NULL 
        AND ve.precinct != ''
        AND v.county IS NOT NULL
        AND v.county != ''
    """, (ELECTION_DATE,))
    
    voting_records = cursor.fetchall()
    total_records = len(voting_records)
    print(f"Processing {total_records:,} voting records...")
    
    # Process in batches
    batch_size = 10000
    assigned = 0
    
    for i in range(0, total_records, batch_size):
        batch = voting_records[i:i+batch_size]
        updates = []
        
        for record_id, vuid, precinct, county in batch:
            variants = PrecinctNormalizer.normalize(precinct, county)
            
            district = None
            for variant in variants:
                cursor.execute("""
                    SELECT state_senate_district
                    FROM precinct_normalized
                    WHERE county = ? AND normalized_precinct = ?
                    AND state_senate_district IS NOT NULL
                    LIMIT 1
                """, (county, variant))
                
                result = cursor.fetchone()
                if result and result[0]:
                    raw_district = result[0]
                    # Normalize format: "15" → "SD-15"
                    if raw_district.isdigit():
                        district = f"SD-{raw_district}"
                    else:
                        district = raw_district
                    break
            
            if district:
                updates.append((district, record_id))
                assigned += 1
        
        if updates:
            cursor.executemany("""
                UPDATE voter_elections 
                SET state_senate_district = ?
                WHERE id = ?
            """, updates)
            conn.commit()
        
        if (i + batch_size) % 100000 == 0:
            print(f"  Processed {min(i + batch_size, total_records):,} / {total_records:,} records...")
    
    match_rate = 100 * assigned / total_records if total_records > 0 else 0
    print(f"✓ Assigned {assigned:,} records ({match_rate:.1f}%)")
    
    return assigned


def generate_district_caches(conn):
    """Generate cache files for House and Senate districts"""
    print("\n4. Generating District Cache Files...")
    cursor = conn.cursor()
    
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if latitude/longitude columns exist
    cursor.execute("PRAGMA table_info(voters)")
    columns = [row[1] for row in cursor.fetchall()]
    has_geocoding = 'latitude' in columns and 'longitude' in columns
    
    # Generate House district caches
    cursor.execute("""
        SELECT DISTINCT state_house_district
        FROM voter_elections
        WHERE election_date = ?
        AND state_house_district IS NOT NULL
        AND state_house_district != ''
        ORDER BY state_house_district
    """, (ELECTION_DATE,))
    
    house_districts = [row[0] for row in cursor.fetchall()]
    print(f"  Generating {len(house_districts)} House district caches...")
    
    for district in house_districts:
        if has_geocoding:
            cursor.execute("""
                SELECT 
                    ve.vuid,
                    v.latitude,
                    v.longitude,
                    ve.party_voted,
                    ve.voting_method,
                    v.county
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE ve.election_date = ?
                AND ve.state_house_district = ?
                AND v.latitude IS NOT NULL
                AND v.longitude IS NOT NULL
            """, (ELECTION_DATE, district))
            
            voters = []
            for row in cursor.fetchall():
                voters.append({
                    'vuid': row[0],
                    'lat': row[1],
                    'lng': row[2],
                    'party': row[3],
                    'method': row[4],
                    'county': row[5]
                })
        else:
            # No geocoding - just count voters
            cursor.execute("""
                SELECT COUNT(DISTINCT ve.vuid)
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE ve.election_date = ?
                AND ve.state_house_district = ?
            """, (ELECTION_DATE, district))
            
            count = cursor.fetchone()[0]
            voters = {'count': count, 'district': district}
        
        if voters:
            cache_file = CACHE_DIR / f"house_{district.lower().replace('-', '_')}.json"
            with open(cache_file, 'w') as f:
                json.dump(voters, f)
    
    print(f"✓ Generated {len(house_districts)} House district caches")
    
    # Generate Senate district caches
    cursor.execute("""
        SELECT DISTINCT state_senate_district
        FROM voter_elections
        WHERE election_date = ?
        AND state_senate_district IS NOT NULL
        AND state_senate_district != ''
        ORDER BY state_senate_district
    """, (ELECTION_DATE,))
    
    senate_districts = [row[0] for row in cursor.fetchall()]
    print(f"  Generating {len(senate_districts)} Senate district caches...")
    
    for district in senate_districts:
        if has_geocoding:
            cursor.execute("""
                SELECT 
                    ve.vuid,
                    v.latitude,
                    v.longitude,
                    ve.party_voted,
                    ve.voting_method,
                    v.county
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE ve.election_date = ?
                AND ve.state_senate_district = ?
                AND v.latitude IS NOT NULL
                AND v.longitude IS NOT NULL
            """, (ELECTION_DATE, district))
            
            voters = []
            for row in cursor.fetchall():
                voters.append({
                    'vuid': row[0],
                    'lat': row[1],
                    'lng': row[2],
                    'party': row[3],
                    'method': row[4],
                    'county': row[5]
                })
        else:
            # No geocoding - just count voters
            cursor.execute("""
                SELECT COUNT(DISTINCT ve.vuid)
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                WHERE ve.election_date = ?
                AND ve.state_senate_district = ?
            """, (ELECTION_DATE, district))
            
            count = cursor.fetchone()[0]
            voters = {'count': count, 'district': district}
        
        if voters:
            cache_file = CACHE_DIR / f"senate_{district.lower().replace('-', '_')}.json"
            with open(cache_file, 'w') as f:
                json.dump(voters, f)
    
    print(f"✓ Generated {len(senate_districts)} Senate district caches")


def show_summary(conn):
    """Show summary statistics"""
    print("\n5. SUMMARY")
    print("=" * 80)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date = ?", (ELECTION_DATE,))
    total = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM voter_elections 
        WHERE election_date = ? AND state_house_district IS NOT NULL AND state_house_district != ''
    """, (ELECTION_DATE,))
    house_assigned = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(*) FROM voter_elections 
        WHERE election_date = ? AND state_senate_district IS NOT NULL AND state_senate_district != ''
    """, (ELECTION_DATE,))
    senate_assigned = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT state_house_district) FROM voter_elections 
        WHERE election_date = ? AND state_house_district IS NOT NULL AND state_house_district != ''
    """, (ELECTION_DATE,))
    house_districts = cursor.fetchone()[0]
    
    cursor.execute("""
        SELECT COUNT(DISTINCT state_senate_district) FROM voter_elections 
        WHERE election_date = ? AND state_senate_district IS NOT NULL AND state_senate_district != ''
    """, (ELECTION_DATE,))
    senate_districts = cursor.fetchone()[0]
    
    print(f"Total voting records:      {total:>10,}")
    print(f"\nState House:")
    print(f"  Assigned voters:         {house_assigned:>10,} ({100*house_assigned/total:.1f}%)")
    print(f"  Unique districts:        {house_districts:>10}")
    print(f"\nState Senate:")
    print(f"  Assigned voters:         {senate_assigned:>10,} ({100*senate_assigned/total:.1f}%)")
    print(f"  Unique districts:        {senate_districts:>10}")


def main():
    print("=" * 80)
    print("BUILD HOUSE AND SENATE DISTRICT ASSIGNMENTS")
    print("=" * 80)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        add_district_columns(conn)
        assign_house_districts(conn)
        assign_senate_districts(conn)
        generate_district_caches(conn)
        show_summary(conn)
        
        print("\n" + "=" * 80)
        print("✓ COMPLETE")
        print("=" * 80)
        
    finally:
        conn.close()


if __name__ == '__main__':
    main()
