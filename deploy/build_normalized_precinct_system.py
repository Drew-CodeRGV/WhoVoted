#!/usr/bin/env python3
"""
BUILD NORMALIZED PRECINCT SYSTEM

This script:
1. Analyzes precinct formats in both reference data and voting records
2. Creates normalization rules (interpreters) for each format
3. Builds a normalized precinct lookup table
4. Assigns districts to voters using normalized matching

The goal: Make it easy to reference precincts regardless of format variations.
"""
import sqlite3
import re
from collections import defaultdict

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'


class PrecinctNormalizer:
    """
    Interprets and normalizes precinct identifiers from various formats.
    """
    
    @staticmethod
    def normalize(precinct, county=None):
        """
        Normalize a precinct identifier to a standard format.
        Returns a set of possible normalized forms for matching.
        """
        if not precinct:
            return set()
        
        p = str(precinct).strip().upper()
        normalized = set()
        
        # Original value
        normalized.add(p)
        
        # Remove all whitespace
        no_space = p.replace(' ', '')
        normalized.add(no_space)
        
        # Extract numeric parts
        numbers = re.findall(r'\d+', p)
        if numbers:
            # Just the numbers concatenated
            normalized.add(''.join(numbers))
            
            # Each number individually
            for num in numbers:
                normalized.add(num)
                normalized.add(num.lstrip('0') or '0')  # Without leading zeros
                normalized.add(num.zfill(4))  # Padded to 4 digits
        
        # Remove common prefixes
        for prefix in ['PCT', 'PRECINCT', 'PRE', 'P', 'S', 'E', 'W', 'N']:
            if p.startswith(prefix):
                suffix = p[len(prefix):].strip()
                if suffix:
                    normalized.add(suffix)
                    # Recursively normalize the suffix
                    normalized.update(PrecinctNormalizer.normalize(suffix))
        
        # Handle decimal formats: "S 3.2" → "S32", "32", "3.2", "302"
        if '.' in p:
            # Remove decimal point
            no_decimal = p.replace('.', '')
            normalized.add(no_decimal)
            
            # Split on decimal and pad: "3.2" → "302"
            parts = p.split('.')
            if len(parts) == 2 and parts[0].strip().isdigit() and parts[1].strip().isdigit():
                major = parts[0].strip()
                minor = parts[1].strip()
                normalized.add(f"{major}{minor.zfill(2)}")
                normalized.add(f"{major.zfill(2)}{minor.zfill(2)}")
        
        # Handle hyphen formats: "3-2" → "32", "302"
        if '-' in p:
            no_hyphen = p.replace('-', '')
            normalized.add(no_hyphen)
            
            parts = p.split('-')
            if len(parts) == 2:
                normalized.add(f"{parts[0]}{parts[1].zfill(2)}")
        
        # Handle slash formats: "3/2" → "32"
        if '/' in p:
            no_slash = p.replace('/', '')
            normalized.add(no_slash)
        
        return normalized


def create_normalized_precinct_table(conn):
    """
    Create a table that stores normalized precinct mappings.
    """
    print("\n=== Creating Normalized Precinct Table ===")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS precinct_normalized (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            county TEXT NOT NULL,
            original_precinct TEXT NOT NULL,
            normalized_precinct TEXT NOT NULL,
            congressional_district TEXT,
            state_senate_district TEXT,
            state_house_district TEXT,
            source TEXT,
            UNIQUE(county, original_precinct, normalized_precinct)
        )
    """)
    
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_precinct_norm_lookup ON precinct_normalized(county, normalized_precinct)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_precinct_norm_district ON precinct_normalized(congressional_district)")
    
    conn.commit()
    print("✓ Table created")


def populate_normalized_mappings(conn):
    """
    Populate the normalized table from precinct_districts.
    For each precinct, generate all normalized variants.
    """
    print("\n=== Populating Normalized Mappings ===")
    cursor = conn.cursor()
    
    # Clear existing data
    cursor.execute("DELETE FROM precinct_normalized")
    
    # Get all precinct mappings
    cursor.execute("""
        SELECT DISTINCT county, precinct, congressional_district, 
               state_senate_district, state_house_district
        FROM precinct_districts
        WHERE precinct IS NOT NULL AND precinct != ''
    """)
    
    mappings = cursor.fetchall()
    print(f"Processing {len(mappings):,} precinct mappings...")
    
    inserts = []
    for county, precinct, cong_dist, senate_dist, house_dist in mappings:
        # Generate all normalized variants
        variants = PrecinctNormalizer.normalize(precinct, county)
        
        for variant in variants:
            inserts.append((
                county or '',
                precinct,
                variant,
                cong_dist,
                senate_dist,
                house_dist,
                'vtd'
            ))
    
    print(f"Generated {len(inserts):,} normalized variants")
    
    # Batch insert
    cursor.executemany("""
        INSERT OR IGNORE INTO precinct_normalized 
        (county, original_precinct, normalized_precinct, congressional_district,
         state_senate_district, state_house_district, source)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, inserts)
    
    conn.commit()
    
    # Show stats
    cursor.execute("SELECT COUNT(*) FROM precinct_normalized")
    total = cursor.fetchone()[0]
    print(f"✓ Inserted {total:,} normalized precinct mappings")
    
    return total


def assign_districts_using_normalized(conn):
    """
    Assign districts to voting records using normalized precinct matching.
    """
    print("\n=== Assigning Districts Using Normalized Matching ===")
    cursor = conn.cursor()
    
    # Get all voting records with precincts (include all data quality levels)
    cursor.execute("""
        SELECT 
            ve.id,
            ve.vuid,
            ve.precinct,
            v.county,
            ve.party_voted
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
    unmatched = 0
    
    for i in range(0, total_records, batch_size):
        batch = voting_records[i:i+batch_size]
        updates = []
        
        for record_id, vuid, precinct, county, party in batch:
            # Generate normalized variants for this voter's precinct
            variants = PrecinctNormalizer.normalize(precinct, county)
            
            # Try to find a match in normalized table
            district = None
            for variant in variants:
                cursor.execute("""
                    SELECT congressional_district
                    FROM precinct_normalized
                    WHERE county = ? AND normalized_precinct = ?
                    LIMIT 1
                """, (county, variant))
                
                result = cursor.fetchone()
                if result and result[0]:
                    # Normalize district format: "15" → "TX-15"
                    raw_district = result[0]
                    if raw_district.isdigit():
                        district = f"TX-{raw_district}"
                    else:
                        district = raw_district
                    break
            
            if district:
                updates.append((district, record_id))
                assigned += 1
            else:
                unmatched += 1
        
        # Batch update
        if updates:
            cursor.executemany("""
                UPDATE voter_elections 
                SET congressional_district = ?
                WHERE id = ?
            """, updates)
            conn.commit()
        
        if (i + batch_size) % 100000 == 0:
            print(f"  Processed {min(i + batch_size, total_records):,} / {total_records:,} records...")
    
    match_rate = 100 * assigned / total_records if total_records > 0 else 0
    print(f"\n✓ Assigned {assigned:,} records ({match_rate:.1f}%)")
    print(f"✗ Unmatched {unmatched:,} records ({100-match_rate:.1f}%)")
    
    return assigned, unmatched


def analyze_unmatched_precincts(conn):
    """
    Analyze precincts that couldn't be matched to help build better interpreters.
    """
    print("\n=== Analyzing Unmatched Precincts ===")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            v.county,
            ve.precinct,
            COUNT(*) as voter_count,
            ve.party_voted
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ?
        AND ve.precinct IS NOT NULL 
        AND ve.precinct != ''
        AND (ve.congressional_district IS NULL OR ve.congressional_district = '')
        GROUP BY v.county, ve.precinct, ve.party_voted
        ORDER BY voter_count DESC
        LIMIT 50
    """, (ELECTION_DATE,))
    
    unmatched = cursor.fetchall()
    
    if unmatched:
        print(f"\nTop unmatched precincts (by voter count):")
        print(f"{'County':<20} {'Precinct':<20} {'Party':<12} {'Voters':>8}")
        print("-" * 62)
        
        for county, precinct, count, party in unmatched[:20]:
            print(f"{county:<20} {precinct:<20} {party:<12} {count:>8,}")
    else:
        print("✓ All precincts matched!")
    
    return len(unmatched)


def verify_d15(conn):
    """
    Verify D15 accuracy.
    """
    print("\n=== D15 VERIFICATION ===")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        WHERE ve.election_date = ?
        AND ve.party_voted = 'Democratic'
        AND ve.congressional_district = 'TX-15'
    """, (ELECTION_DATE,))
    
    d15_count = cursor.fetchone()[0]
    official = 54573
    diff = d15_count - official
    accuracy = 100 * (1 - abs(diff) / official) if official > 0 else 0
    
    print(f"\nD15 Democratic Voters:")
    print(f"  Database:  {d15_count:>8,}")
    print(f"  Official:  {official:>8,}")
    print(f"  Difference: {diff:>+8,}")
    print(f"  Accuracy:  {accuracy:>8.2f}%")
    
    if abs(diff) == 0:
        print("\n✓✓✓ PERFECT MATCH!")
    elif abs(diff) <= 100:
        print("\n✓✓ EXCELLENT")
    elif accuracy >= 99:
        print("\n✓ GOOD")
    else:
        print("\n⚠ Needs work")
    
    # Breakdown by county
    print("\nD15 by County:")
    cursor.execute("""
        SELECT v.county, COUNT(DISTINCT ve.vuid) as count
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ?
        AND ve.party_voted = 'Democratic'
        AND ve.congressional_district = 'TX-15'
        GROUP BY v.county
        ORDER BY count DESC
    """, (ELECTION_DATE,))
    
    for county, count in cursor.fetchall():
        print(f"  {county:<20} {count:>8,}")
    
    return accuracy, d15_count


def show_summary(conn):
    """
    Show overall summary statistics.
    """
    print("\n=== SUMMARY ===")
    cursor = conn.cursor()
    
    # Total voting records
    cursor.execute("""
        SELECT COUNT(*) FROM voter_elections 
        WHERE election_date = ?
    """, (ELECTION_DATE,))
    total_votes = cursor.fetchone()[0]
    
    # Assigned to districts
    cursor.execute("""
        SELECT COUNT(*) FROM voter_elections 
        WHERE election_date = ?
        AND congressional_district IS NOT NULL
        AND congressional_district != ''
    """, (ELECTION_DATE,))
    assigned = cursor.fetchone()[0]
    
    # Coverage
    coverage = 100 * assigned / total_votes if total_votes > 0 else 0
    
    print(f"Total voting records:    {total_votes:>10,}")
    print(f"Assigned to districts:   {assigned:>10,}")
    print(f"Coverage:                {coverage:>10.1f}%")
    
    # District count
    cursor.execute("""
        SELECT COUNT(DISTINCT congressional_district)
        FROM voter_elections
        WHERE election_date = ?
        AND congressional_district IS NOT NULL
        AND congressional_district != ''
    """, (ELECTION_DATE,))
    district_count = cursor.fetchone()[0]
    print(f"Districts covered:       {district_count:>10}")


def main():
    print("=" * 70)
    print("BUILD NORMALIZED PRECINCT SYSTEM")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Step 1: Create normalized table
        create_normalized_precinct_table(conn)
        
        # Step 2: Populate with normalized mappings
        mapping_count = populate_normalized_mappings(conn)
        
        if mapping_count == 0:
            print("\nERROR: No precinct mappings found!")
            print("Run parse_vtd_correctly.py first to build precinct_districts table")
            return 1
        
        # Step 3: Assign districts using normalized matching
        assigned, unmatched = assign_districts_using_normalized(conn)
        
        # Step 4: Analyze unmatched precincts
        unmatched_count = analyze_unmatched_precincts(conn)
        
        # Step 5: Verify D15
        d15_accuracy, d15_count = verify_d15(conn)
        
        # Step 6: Show summary
        show_summary(conn)
        
        print("\n" + "=" * 70)
        if d15_accuracy >= 99:
            print("✓ SUCCESS - Ready for production")
            return 0
        elif d15_accuracy >= 95:
            print("✓ GOOD PROGRESS - Continue refining")
            return 0
        else:
            print("⚠ MORE WORK NEEDED")
            return 1
        
    finally:
        conn.close()


if __name__ == '__main__':
    exit(main())
