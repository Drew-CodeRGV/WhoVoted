#!/usr/bin/env python3
"""
DEFINITIVE DISTRICT ASSIGNMENT SOLUTION

Top-Down: Congressional District → Counties → Precincts
Bottom-Up: Voter → Voted in Precinct → County
Middle: Match voter's (precinct + county) to district's (precinct + county)

The answer is in the middle - tie the voter precinct to the county precinct 
that's in the district.
"""
import sqlite3
import json
from pathlib import Path
from collections import defaultdict

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-03-03'

def build_district_precinct_map(conn):
    """
    TOP-DOWN: Build complete map of District → County → Precincts
    
    Returns: {
        'TX-15': {
            'Hidalgo': ['0001', '0002', ...],
            'Brooks': ['101', '102', ...],
            ...
        },
        'TX-34': {...},
        ...
    }
    """
    print("\n=== TOP-DOWN: Building District → County → Precinct Map ===")
    
    district_map = defaultdict(lambda: defaultdict(list))
    cursor = conn.cursor()
    
    # Get all precinct mappings from precinct_districts table
    cursor.execute("""
        SELECT DISTINCT county, precinct, congressional_district
        FROM precinct_districts
        WHERE congressional_district IS NOT NULL
        AND congressional_district != ''
        ORDER BY congressional_district, county, precinct
    """)
    
    count = 0
    for county, precinct, district in cursor.fetchall():
        if county and precinct and district:
            district_map[district][county].append(precinct)
            count += 1
    
    print(f"✓ Loaded {count:,} precinct mappings")
    print(f"✓ Covering {len(district_map)} districts")
    
    # Show sample
    print("\nSample - TX-15 precincts by county:")
    if 'TX-15' in district_map:
        for county in sorted(district_map['TX-15'].keys())[:5]:
            precinct_count = len(district_map['TX-15'][county])
            sample_precincts = district_map['TX-15'][county][:3]
            print(f"  {county}: {precinct_count} precincts (e.g., {', '.join(sample_precincts)})")
    
    return district_map


def build_voter_precinct_map(conn):
    """
    BOTTOM-UP: Build map of Voter → Precinct + County
    
    Returns: {
        'vuid123': {'precinct': '0001', 'county': 'Hidalgo', 'party': 'Democratic'},
        ...
    }
    """
    print("\n=== BOTTOM-UP: Building Voter → Precinct + County Map ===")
    
    cursor = conn.cursor()
    
    # Get all voters who voted, with their precinct and county
    cursor.execute("""
        SELECT 
            ve.vuid,
            ve.precinct as voting_precinct,
            v.county,
            ve.party_voted,
            ve.id as record_id
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ?
        AND ve.precinct IS NOT NULL 
        AND ve.precinct != ''
        AND v.county IS NOT NULL
        AND v.county != ''
    """, (ELECTION_DATE,))
    
    voter_map = {}
    for vuid, precinct, county, party, record_id in cursor.fetchall():
        voter_map[record_id] = {
            'vuid': vuid,
            'precinct': precinct,
            'county': county,
            'party': party
        }
    
    print(f"✓ Loaded {len(voter_map):,} voting records with precinct data")
    
    # Show sample
    print("\nSample voting records:")
    for i, (record_id, data) in enumerate(list(voter_map.items())[:5]):
        print(f"  Record {record_id}: Precinct '{data['precinct']}' in {data['county']} County ({data['party']})")
    
    return voter_map


def normalize_precinct(precinct):
    """
    Generate all possible variants of a precinct identifier for matching.
    """
    if not precinct:
        return set()
    
    p = str(precinct).strip().upper()
    variants = {p}
    
    # Remove leading zeros: '0001' → '1'
    if p and p[0] == '0':
        variants.add(p.lstrip('0') or '0')
    
    # Pad to 4 digits if numeric: '1' → '0001'
    if p.isdigit():
        variants.add(p.zfill(4))
    
    # Remove common prefixes: 'PCT001' → '001'
    for prefix in ['PCT', 'PRECINCT', 'P', 'PRE']:
        if p.startswith(prefix):
            suffix = p[len(prefix):].strip()
            if suffix:
                variants.add(suffix)
                # Also try normalized version of suffix
                if suffix.isdigit():
                    variants.add(suffix.lstrip('0') or '0')
                    variants.add(suffix.zfill(4))
    
    return variants


def match_in_middle(district_map, voter_map):
    """
    THE MIDDLE: Match voter (precinct + county) to district (precinct + county)
    
    For each voter:
    1. Get their voting precinct and county
    2. Normalize the precinct (handle format variations)
    3. Look up which district contains that (precinct + county) combination
    4. Assign the district to that voter
    """
    print("\n=== THE MIDDLE: Matching Voters to Districts ===")
    
    # Build reverse lookup: (county, precinct_variant) → district
    precinct_lookup = {}
    for district, counties in district_map.items():
        for county, precincts in counties.items():
            for precinct in precincts:
                # Store all variants of this precinct
                for variant in normalize_precinct(precinct):
                    key = (county.upper(), variant)
                    if key not in precinct_lookup:
                        precinct_lookup[key] = district
    
    print(f"✓ Built lookup table with {len(precinct_lookup):,} (county, precinct) combinations")
    
    # Match voters to districts
    matches = {}
    unmatched = []
    
    for record_id, voter_data in voter_map.items():
        county = voter_data['county'].upper()
        precinct = voter_data['precinct']
        
        # Try all variants of the voter's precinct
        district = None
        for variant in normalize_precinct(precinct):
            key = (county, variant)
            if key in precinct_lookup:
                district = precinct_lookup[key]
                break
        
        if district:
            matches[record_id] = {
                'vuid': voter_data['vuid'],
                'district': district,
                'county': voter_data['county'],
                'precinct': voter_data['precinct'],
                'party': voter_data['party']
            }
        else:
            unmatched.append({
                'record_id': record_id,
                'county': voter_data['county'],
                'precinct': voter_data['precinct'],
                'party': voter_data['party']
            })
    
    match_rate = 100 * len(matches) / len(voter_map) if voter_map else 0
    print(f"✓ Matched {len(matches):,} voters to districts ({match_rate:.1f}%)")
    print(f"✗ Could not match {len(unmatched):,} voters ({100-match_rate:.1f}%)")
    
    if unmatched:
        print("\nSample unmatched voters:")
        for voter in unmatched[:10]:
            print(f"  {voter['county']} County, Precinct '{voter['precinct']}' ({voter['party']})")
    
    return matches, unmatched


def update_database(conn, matches):
    """
    Update voter_elections table with district assignments.
    """
    print("\n=== Updating Database ===")
    cursor = conn.cursor()
    
    # Ensure column exists
    try:
        cursor.execute("ALTER TABLE voter_elections ADD COLUMN congressional_district TEXT")
        conn.commit()
    except:
        pass
    
    # Update in batches
    batch_size = 5000
    updated = 0
    
    match_list = list(matches.items())
    for i in range(0, len(match_list), batch_size):
        batch = match_list[i:i+batch_size]
        
        for record_id, data in batch:
            cursor.execute("""
                UPDATE voter_elections 
                SET congressional_district = ?
                WHERE id = ?
            """, (data['district'], record_id))
            updated += 1
        
        conn.commit()
        
        if (i + batch_size) % 50000 == 0:
            print(f"  Updated {i + batch_size:,} / {len(match_list):,} records...")
    
    print(f"✓ Updated {updated:,} voting records with district assignments")
    return updated


def verify_d15(conn):
    """
    Verify D15 matches official count of 54,573.
    """
    print("\n=== VERIFICATION: D15 Accuracy ===")
    cursor = conn.cursor()
    
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
    
    print(f"\nD15 Democratic Voters:")
    print(f"  Database:  {d15_count:>8,}")
    print(f"  Official:  {official_count:>8,}")
    print(f"  Difference: {difference:>+8,}")
    print(f"  Accuracy:  {accuracy:>8.2f}%")
    
    if abs(difference) == 0:
        print("\n✓✓✓ PERFECT MATCH! ✓✓✓")
    elif abs(difference) <= 50:
        print("\n✓✓ EXCELLENT - Within 50 votes!")
    elif abs(difference) <= 100:
        print("\n✓ VERY GOOD - Within 100 votes")
    elif accuracy >= 99:
        print("\n✓ GOOD - Within 1%")
    else:
        print("\n⚠ Needs improvement")
    
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
        print(f"  {county:<20} {count:>8,}")
    
    return accuracy, d15_count


def verify_all_districts(conn):
    """
    Show all congressional districts with voter counts.
    """
    print("\n=== ALL CONGRESSIONAL DISTRICTS ===")
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            ve.congressional_district,
            COUNT(DISTINCT ve.vuid) as total,
            COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
            COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep
        FROM voter_elections ve
        WHERE ve.election_date = ?
        AND ve.congressional_district IS NOT NULL
        AND ve.congressional_district != ''
        GROUP BY ve.congressional_district
        ORDER BY ve.congressional_district
    """, (ELECTION_DATE,))
    
    results = cursor.fetchall()
    
    print(f"\n{'District':<12} {'Total':>12} {'Dem':>12} {'Rep':>12}")
    print("-" * 50)
    
    total_all = 0
    total_dem = 0
    total_rep = 0
    
    for district, total, dem, rep in results:
        print(f"{district:<12} {total:>12,} {dem:>12,} {rep:>12,}")
        total_all += total
        total_dem += dem
        total_rep += rep
    
    print("-" * 50)
    print(f"{'TOTAL':<12} {total_all:>12,} {total_dem:>12,} {total_rep:>12,}")
    
    # Show unassigned
    cursor.execute("""
        SELECT COUNT(DISTINCT vuid)
        FROM voter_elections
        WHERE election_date = ?
        AND (congressional_district IS NULL OR congressional_district = '')
    """, (ELECTION_DATE,))
    
    unassigned = cursor.fetchone()[0]
    print(f"{'UNASSIGNED':<12} {unassigned:>12,}")
    
    coverage = 100 * total_all / (total_all + unassigned) if (total_all + unassigned) > 0 else 0
    print(f"\nCoverage: {coverage:.1f}%")
    
    return len(results), coverage


def main():
    print("=" * 70)
    print("CONNECT VOTERS TO DISTRICTS")
    print("Top-Down meets Bottom-Up in the Middle")
    print("=" * 70)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    try:
        # Step 1: TOP-DOWN - Build district → county → precinct map
        district_map = build_district_precinct_map(conn)
        
        if not district_map:
            print("\nERROR: No district-precinct mappings found!")
            print("Please run parse_vtd_correctly.py first to build precinct_districts table")
            return 1
        
        # Step 2: BOTTOM-UP - Build voter → precinct + county map
        voter_map = build_voter_precinct_map(conn)
        
        if not voter_map:
            print("\nERROR: No voting records with precinct data found!")
            return 1
        
        # Step 3: THE MIDDLE - Match them together
        matches, unmatched = match_in_middle(district_map, voter_map)
        
        if not matches:
            print("\nERROR: Could not match any voters to districts!")
            return 1
        
        # Step 4: Update database
        updated = update_database(conn, matches)
        
        # Step 5: Verify D15
        d15_accuracy, d15_count = verify_d15(conn)
        
        # Step 6: Show all districts
        district_count, coverage = verify_all_districts(conn)
        
        # Summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"Districts mapped:        {len(district_map)}")
        print(f"Voting records:          {len(voter_map):,}")
        print(f"Successful matches:      {len(matches):,} ({100*len(matches)/len(voter_map):.1f}%)")
        print(f"Database updated:        {updated:,} records")
        print(f"District coverage:       {coverage:.1f}%")
        print(f"D15 count:               {d15_count:,} (target: 54,573)")
        print(f"D15 accuracy:            {d15_accuracy:.2f}%")
        
        if d15_accuracy >= 99.5:
            print("\n✓✓✓ SUCCESS - Production ready!")
            return 0
        elif d15_accuracy >= 98:
            print("\n✓✓ VERY CLOSE - Minor adjustments needed")
            return 0
        elif d15_accuracy >= 95:
            print("\n✓ GOOD PROGRESS - Continue refining")
            return 1
        else:
            print("\n⚠ MORE WORK NEEDED")
            return 1
        
    finally:
        conn.close()


if __name__ == '__main__':
    exit(main())
