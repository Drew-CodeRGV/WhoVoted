#!/usr/bin/env python3
"""
CRITICAL FIX: Use voter_elections.precinct (where they actually voted) 
instead of voters.precinct (where they're registered) for district assignment.

This is the authoritative source - when voters vote, the system records 
EXACTLY which precinct they voted in. We should use THAT data.

Strategy:
1. Build complete precinct-to-district mapping from ALL sources
2. Match voter_elections.precinct + county to precinct_districts
3. Assign districts based on where they actually voted
4. Verify D15 = 54,573 exactly
"""
import sqlite3
import json
from pathlib import Path

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

def load_all_precinct_mappings(conn):
    """Load precinct mappings from ALL available sources."""
    print("\n=== Loading Precinct-to-District Mappings ===")
    
    # Source 1: VTD files (already in precinct_districts table)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM precinct_districts")
    vtd_count = cursor.fetchone()[0]
    print(f"✓ VTD files: {vtd_count:,} precinct mappings")
    
    # Source 2: JSON precinct files
    json_dir = Path('/opt/whovoted/data/district_reference')
    json_count = 0
    
    if json_dir.exists():
        for json_file in json_dir.glob('*.json'):
            try:
                with open(json_file) as f:
                    data = json.load(f)
                    
                # Handle different JSON structures
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, dict) and 'precincts' in value:
                            # Format: {district: {precincts: [...], ...}}
                            district = key
                            for precinct_info in value['precincts']:
                                if isinstance(precinct_info, dict):
                                    precinct = precinct_info.get('precinct') or precinct_info.get('name')
                                    county = precinct_info.get('county', '')
                                else:
                                    precinct = str(precinct_info)
                                    county = ''
                                
                                if precinct:
                                    cursor.execute("""
                                        INSERT OR IGNORE INTO precinct_districts 
                                        (county, precinct, congressional_district, source)
                                        VALUES (?, ?, ?, ?)
                                    """, (county, str(precinct), district, f'json:{json_file.name}'))
                                    json_count += 1
                        elif isinstance(value, list):
                            # Format: {district: [precinct1, precinct2, ...]}
                            district = key
                            for precinct in value:
                                cursor.execute("""
                                    INSERT OR IGNORE INTO precinct_districts 
                                    (county, precinct, congressional_district, source)
                                    VALUES (?, ?, ?, ?)
                                """, ('', str(precinct), district, f'json:{json_file.name}'))
                                json_count += 1
                elif isinstance(data, list):
                    # Format: [{precinct: ..., district: ..., county: ...}, ...]
                    for item in data:
                        if isinstance(item, dict):
                            precinct = item.get('precinct') or item.get('name')
                            district = item.get('district') or item.get('congressional_district')
                            county = item.get('county', '')
                            
                            if precinct and district:
                                cursor.execute("""
                                    INSERT OR IGNORE INTO precinct_districts 
                                    (county, precinct, congressional_district, source)
                                    VALUES (?, ?, ?, ?)
                                """, (county, str(precinct), district, f'json:{json_file.name}'))
                                json_count += 1
            except Exception as e:
                print(f"  Warning: Could not parse {json_file.name}: {e}")
    
    conn.commit()
    print(f"✓ JSON files: {json_count:,} additional mappings")
    
    # Get final count
    cursor.execute("SELECT COUNT(*) FROM precinct_districts")
    total_count = cursor.fetchone()[0]
    print(f"✓ Total precinct mappings: {total_count:,}")
    
    return total_count


def normalize_precinct(precinct):
    """Normalize precinct for flexible matching."""
    if not precinct:
        return []
    
    p = str(precinct).strip().upper()
    variants = [p]
    
    # Remove leading zeros
    if p and p[0] == '0':
        variants.append(p.lstrip('0'))
    
    # Pad to 4 digits if numeric
    if p.isdigit():
        variants.append(p.zfill(4))
    
    # Remove common prefixes
    for prefix in ['PCT', 'PRECINCT', 'P']:
        if p.startswith(prefix):
            variants.append(p[len(prefix):].strip())
    
    return list(set(variants))


def assign_districts_from_voting_precincts(conn):
    """
    Assign districts using voter_elections.precinct (where they actually voted).
    This is the KEY FIX - use the voting record precinct, not registration precinct.
    """
    print("\n=== Assigning Districts from Voting Precincts ===")
    cursor = conn.cursor()
    
    # Get all voting records with precincts
    cursor.execute("""
        SELECT 
            ve.id,
            ve.vuid,
            ve.precinct as voting_precinct,
            v.county,
            v.precinct as registration_precinct
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
    print(f"Found {total_records:,} voting records with precinct data")
    
    if total_records == 0:
        print("ERROR: No voting records with precinct data found!")
        return 0
    
    # Add district columns if they don't exist
    try:
        cursor.execute("ALTER TABLE voter_elections ADD COLUMN congressional_district TEXT")
        conn.commit()
    except:
        pass
    
    try:
        cursor.execute("ALTER TABLE voter_elections ADD COLUMN state_senate_district TEXT")
        conn.commit()
    except:
        pass
    
    try:
        cursor.execute("ALTER TABLE voter_elections ADD COLUMN state_house_district TEXT")
        conn.commit()
    except:
        pass
    
    # Process in batches
    batch_size = 10000
    assigned = 0
    unmatched = 0
    
    for i in range(0, total_records, batch_size):
        batch = voting_records[i:i+batch_size]
        
        for record in batch:
            record_id, vuid, voting_precinct, county, reg_precinct = record
            
            # Try to match voting precinct first (PRIORITY)
            variants = normalize_precinct(voting_precinct)
            district = None
            
            for variant in variants:
                cursor.execute("""
                    SELECT congressional_district 
                    FROM precinct_districts 
                    WHERE (county = ? OR county = '' OR county IS NULL)
                    AND precinct = ?
                    LIMIT 1
                """, (county, variant))
                
                result = cursor.fetchone()
                if result and result[0]:
                    district = result[0]
                    break
            
            # Fallback: Try registration precinct if voting precinct didn't match
            if not district and reg_precinct:
                variants = normalize_precinct(reg_precinct)
                for variant in variants:
                    cursor.execute("""
                        SELECT congressional_district 
                        FROM precinct_districts 
                        WHERE (county = ? OR county = '' OR county IS NULL)
                        AND precinct = ?
                        LIMIT 1
                    """, (county, variant))
                    
                    result = cursor.fetchone()
                    if result and result[0]:
                        district = result[0]
                        break
            
            if district:
                # Update the voting record with district
                cursor.execute("""
                    UPDATE voter_elections 
                    SET congressional_district = ?
                    WHERE id = ?
                """, (district, record_id))
                assigned += 1
            else:
                unmatched += 1
        
        if (i + batch_size) % 50000 == 0:
            conn.commit()
            print(f"  Processed {i + batch_size:,} / {total_records:,} records...")
    
    conn.commit()
    
    print(f"\n✓ Assigned districts to {assigned:,} voting records ({100*assigned/total_records:.1f}%)")
    print(f"✗ Could not match {unmatched:,} voting records ({100*unmatched/total_records:.1f}%)")
    
    return assigned


def verify_d15_accuracy(conn):
    """Verify D15 matches the official count of 54,573."""
    print("\n=== Verifying D15 Accuracy ===")
    cursor = conn.cursor()
    
    # Count D15 Democratic voters using voting records
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        WHERE ve.election_date = ?
        AND ve.party_voted = 'Democratic'
        AND ve.congressional_district = 'TX-15'
    """, (ELECTION_DATE,))
    
    d15_count = cursor.fetchone()[0]
    official_count = 54573
    difference = d15_count - official_count
    accuracy = 100 * (1 - abs(difference) / official_count) if official_count > 0 else 0
    
    print(f"D15 Democratic Voters:")
    print(f"  Database: {d15_count:,}")
    print(f"  Official: {official_count:,}")
    print(f"  Difference: {difference:+,}")
    print(f"  Accuracy: {accuracy:.2f}%")
    
    if abs(difference) <= 100:
        print("✓ EXCELLENT - Within 100 votes!")
    elif accuracy >= 99:
        print("✓ GOOD - Within 1%")
    elif accuracy >= 95:
        print("⚠ ACCEPTABLE - Within 5%")
    else:
        print("✗ NEEDS WORK - More than 5% off")
    
    # Show breakdown by county
    print("\nD15 Breakdown by County:")
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
        print(f"  {county}: {count:,}")
    
    return accuracy


def verify_all_districts(conn):
    """Show coverage for all congressional districts."""
    print("\n=== All Congressional Districts ===")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            ve.congressional_district,
            COUNT(DISTINCT ve.vuid) as total_voters,
            COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem_voters,
            COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep_voters
        FROM voter_elections ve
        WHERE ve.election_date = ?
        AND ve.congressional_district IS NOT NULL
        AND ve.congressional_district != ''
        GROUP BY ve.congressional_district
        ORDER BY ve.congressional_district
    """, (ELECTION_DATE,))
    
    results = cursor.fetchall()
    
    print(f"{'District':<12} {'Total':>10} {'Dem':>10} {'Rep':>10}")
    print("-" * 44)
    
    total_all = 0
    total_dem = 0
    total_rep = 0
    
    for district, total, dem, rep in results:
        print(f"{district:<12} {total:>10,} {dem:>10,} {rep:>10,}")
        total_all += total
        total_dem += dem
        total_rep += rep
    
    print("-" * 44)
    print(f"{'TOTAL':<12} {total_all:>10,} {total_dem:>10,} {total_rep:>10,}")
    
    # Show unassigned
    cursor.execute("""
        SELECT COUNT(DISTINCT vuid)
        FROM voter_elections
        WHERE election_date = ?
        AND (congressional_district IS NULL OR congressional_district = '')
    """, (ELECTION_DATE,))
    
    unassigned = cursor.fetchone()[0]
    print(f"{'UNASSIGNED':<12} {unassigned:>10,}")
    
    return len(results)


def main():
    print("=" * 60)
    print("DISTRICT ASSIGNMENT FIX")
    print("Using voter_elections.precinct (where they actually voted)")
    print("=" * 60)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Step 1: Load all precinct mappings
        total_mappings = load_all_precinct_mappings(conn)
        
        if total_mappings == 0:
            print("\nERROR: No precinct mappings found!")
            print("Please run parse_vtd_correctly.py first to build precinct_districts table")
            return 1
        
        # Step 2: Assign districts using voting precincts
        assigned = assign_districts_from_voting_precincts(conn)
        
        if assigned == 0:
            print("\nERROR: Could not assign any districts!")
            return 1
        
        # Step 3: Verify D15
        d15_accuracy = verify_d15_accuracy(conn)
        
        # Step 4: Show all districts
        district_count = verify_all_districts(conn)
        
        print("\n" + "=" * 60)
        print("SUMMARY")
        print("=" * 60)
        print(f"Precinct mappings: {total_mappings:,}")
        print(f"Voting records assigned: {assigned:,}")
        print(f"Districts covered: {district_count}")
        print(f"D15 accuracy: {d15_accuracy:.2f}%")
        
        if d15_accuracy >= 99:
            print("\n✓ SUCCESS - Ready for production!")
            return 0
        else:
            print("\n⚠ NEEDS MORE WORK - See details above")
            return 1
        
    finally:
        conn.close()


if __name__ == '__main__':
    exit(main())
