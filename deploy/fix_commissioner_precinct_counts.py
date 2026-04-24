#!/usr/bin/env python3
"""
Fix Commissioner Precinct vote counts by properly mapping voting precincts to commissioner precincts.

This script uses the same approach as TX-15 district assignment:
1. Identifies which voting precincts belong to each commissioner precinct
2. Gets voter data with their precinct information
3. Counts only VUIDs that are in precincts belonging to each commissioner precinct
4. Tallies votes from early voting and election day records for those VUIDs

Uses SQLite database.
"""

import sqlite3
import json
from collections import defaultdict

# Database connection
DB_PATH = '/opt/whovoted/data/whovoted.db'
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Election parameters
COUNTY = 'Hidalgo'
YEAR = 2026
ELECTION_DATE = '2026-03-03'

def load_commissioner_precinct_boundaries():
    """Load commissioner precinct boundaries from districts.json."""
    import json
    
    districts_file = '/opt/whovoted/public/data/districts.json'
    with open(districts_file, 'r') as f:
        data = json.load(f)
    
    commissioner_precincts = {}
    for feature in data.get('features', []):
        props = feature.get('properties', {})
        if props.get('district_type') == 'commissioner':
            district_id = props.get('district_id')
            geometry = feature.get('geometry')
            commissioner_precincts[district_id] = geometry
    
    return commissioner_precincts


def point_in_polygon(lng, lat, geometry):
    """Check if a point is inside a polygon using ray-casting algorithm."""
    gtype = geometry.get('type', '')
    coords = geometry.get('coordinates', [])
    
    if gtype == 'Polygon':
        return _point_in_ring(lng, lat, coords[0])
    elif gtype == 'MultiPolygon':
        for poly in coords:
            if _point_in_ring(lng, lat, poly[0]):
                return True
        return False
    return False


def _point_in_ring(lng, lat, ring):
    """Ray-casting algorithm for a single ring."""
    inside = False
    n = len(ring)
    p1_lng, p1_lat = ring[0]
    
    for i in range(1, n + 1):
        p2_lng, p2_lat = ring[i % n]
        if lat > min(p1_lat, p2_lat):
            if lat <= max(p1_lat, p2_lat):
                if lng <= max(p1_lng, p2_lng):
                    if p1_lat != p2_lat:
                        x_inters = (lat - p1_lat) * (p2_lng - p1_lng) / (p2_lat - p1_lat) + p1_lng
                    if p1_lng == p2_lng or lng <= x_inters:
                        inside = not inside
        p1_lng, p1_lat = p2_lng, p2_lat
    
    return inside


def get_precinct_to_commissioner_mapping():
    """
    Map voting precincts to commissioner precincts using actual polygon boundaries.
    
    This uses the same approach as TX-15:
    1. Get all voting precincts with their centroid locations
    2. Check which commissioner precinct polygon contains each precinct centroid
    3. Return mapping of precinct -> commissioner_precinct_id
    """
    
    print("\n" + "="*80)
    print("MAPPING VOTING PRECINCTS TO COMMISSIONER PRECINCTS")
    print("="*80)
    
    # Load commissioner precinct boundaries
    commissioner_boundaries = load_commissioner_precinct_boundaries()
    print(f"\nLoaded {len(commissioner_boundaries)} commissioner precinct boundaries")
    
    cur = conn.cursor()
    
    # Get all unique voting precincts with their centroid locations
    # Use average lat/lng of all voters in that precinct
    cur.execute("""
        SELECT DISTINCT 
            precinct,
            AVG(lat) as avg_lat,
            AVG(lng) as avg_lon,
            COUNT(*) as voter_count
        FROM voters
        WHERE county = ?
        AND precinct IS NOT NULL
        AND precinct != ''
        AND lat IS NOT NULL
        AND lng IS NOT NULL
        GROUP BY precinct
        ORDER BY precinct
    """, (COUNTY,))
    
    precincts = cur.fetchall()
    print(f"Found {len(precincts)} unique voting precincts in {COUNTY} County")
    
    precinct_to_commissioner = {}
    unassigned_precincts = []
    
    for precinct, avg_lat, avg_lon, voter_count in precincts:
        # Check which commissioner precinct contains this voting precinct's centroid
        assigned = False
        for commissioner_id, geometry in commissioner_boundaries.items():
            if point_in_polygon(avg_lon, avg_lat, geometry):
                precinct_to_commissioner[precinct] = commissioner_id
                print(f"  {precinct} -> {commissioner_id} (lat={avg_lat:.4f}, lon={avg_lon:.4f}, voters={voter_count})")
                assigned = True
                break
        
        if not assigned:
            unassigned_precincts.append((precinct, avg_lat, avg_lon, voter_count))
            print(f"  {precinct} -> UNASSIGNED (lat={avg_lat:.4f}, lon={avg_lon:.4f}, voters={voter_count})")
    
    if unassigned_precincts:
        print(f"\n⚠ WARNING: {len(unassigned_precincts)} precincts could not be assigned to any commissioner precinct")
        print("  These precincts will be excluded from the counts.")
    
    # Summary by commissioner precinct
    print("\nPrecinct assignment summary:")
    for commissioner_id in sorted(commissioner_boundaries.keys()):
        count = sum(1 for p in precinct_to_commissioner.values() if p == commissioner_id)
        print(f"  {commissioner_id}: {count} voting precincts")
    
    cur.close()
    return precinct_to_commissioner


def get_commissioner_precinct_stats(precinct_mapping):
    """
    Calculate statistics for each commissioner precinct based on the precinct mapping.
    
    Uses the same logic as TX-15:
    - Find all voters whose precinct is in the list for this commissioner precinct
    - Count their votes from early_voting and election_day tables
    - Calculate party breakdown, turnout, etc.
    """
    
    print("\n" + "="*80)
    print("CALCULATING COMMISSIONER PRECINCT STATISTICS")
    print("="*80)
    
    cur = conn.cursor()
    
    stats = {}
    
    for commissioner_id in ['CPct-1', 'CPct-2', 'CPct-3', 'CPct-4']:
        print(f"\n{commissioner_id}:")
        
        # Get precincts that belong to this commissioner precinct
        precincts_in_commissioner = [p for p, c in precinct_mapping.items() if c == commissioner_id]
        
        if not precincts_in_commissioner:
            print(f"  ⚠ No precincts found")
            stats[commissioner_id] = {
                'total_voters': 0,
                'voted': 0,
                'not_voted': 0,
                'turnout_pct': 0,
                'dem': 0,
                'rep': 0,
                'precincts': []
            }
            continue
        
        print(f"  Precincts: {len(precincts_in_commissioner)}")
        if len(precincts_in_commissioner) <= 10:
            print(f"    {', '.join(sorted(precincts_in_commissioner))}")
        else:
            print(f"    {', '.join(sorted(precincts_in_commissioner)[:10])}... (+{len(precincts_in_commissioner)-10} more)")
        
        # Create placeholders for SQL IN clause
        placeholders = ','.join('?' * len(precincts_in_commissioner))
        
        # Get total registered voters in these precincts
        cur.execute(f"""
            SELECT COUNT(DISTINCT vuid)
            FROM voters
            WHERE county = ?
            AND precinct IN ({placeholders})
        """, [COUNTY] + precincts_in_commissioner)
        
        total_voters = cur.fetchone()[0]
        print(f"  Total Registered Voters: {total_voters:,}")
        
        # Get voters who voted (from early_voting table)
        # Note: SQLite doesn't have early_voting/election_day tables, using voter_elections
        cur.execute(f"""
            SELECT COUNT(DISTINCT v.vuid)
            FROM voters v
            INNER JOIN voter_elections ve ON v.vuid = ve.vuid
            WHERE v.county = ?
            AND v.precinct IN ({placeholders})
            AND ve.election_date = ?
            AND ve.voting_method = 'Early Voting'
        """, [COUNTY] + precincts_in_commissioner + [ELECTION_DATE])
        
        voted_early = cur.fetchone()[0]
        
        # Get voters who voted on election day
        cur.execute(f"""
            SELECT COUNT(DISTINCT v.vuid)
            FROM voters v
            INNER JOIN voter_elections ve ON v.vuid = ve.vuid
            WHERE v.county = ?
            AND v.precinct IN ({placeholders})
            AND ve.election_date = ?
            AND ve.voting_method = 'Election Day'
        """, [COUNTY] + precincts_in_commissioner + [ELECTION_DATE])
        
        voted_election_day = cur.fetchone()[0]
        
        # Total unique voters (union of early and election day)
        cur.execute(f"""
            SELECT COUNT(DISTINCT v.vuid)
            FROM voters v
            INNER JOIN voter_elections ve ON v.vuid = ve.vuid
            WHERE v.county = ?
            AND v.precinct IN ({placeholders})
            AND ve.election_date = ?
        """, [COUNTY] + precincts_in_commissioner + [ELECTION_DATE])
        
        total_voted = cur.fetchone()[0]
        
        # Get party breakdown for voters who voted
        cur.execute(f"""
            SELECT 
                COALESCE(ve.party_voted, 'Unknown') as party,
                COUNT(DISTINCT ve.vuid) as count
            FROM voter_elections ve
            INNER JOIN voters v ON ve.vuid = v.vuid
            WHERE v.county = ?
            AND v.precinct IN ({placeholders})
            AND ve.election_date = ?
            GROUP BY party
        """, [COUNTY] + precincts_in_commissioner + [ELECTION_DATE])
        
        party_breakdown = dict(cur.fetchall())
        
        # Map party codes to standard names
        # Common codes: DEM, REP, D, R, Democratic, Republican
        dem = 0
        rep = 0
        for party, count in party_breakdown.items():
            party_upper = str(party).upper()
            if party_upper in ('DEM', 'D', 'DEMOCRATIC'):
                dem += count
            elif party_upper in ('REP', 'R', 'REPUBLICAN'):
                rep += count
        
        turnout_pct = (total_voted / total_voters * 100) if total_voters > 0 else 0
        
        stats[commissioner_id] = {
            'total_voters': total_voters,
            'voted': total_voted,
            'voted_early': voted_early,
            'voted_election_day': voted_election_day,
            'not_voted': total_voters - total_voted,
            'turnout_pct': round(turnout_pct, 2),
            'dem': dem,
            'rep': rep,
            'party_breakdown': party_breakdown,
            'precincts': sorted(precincts_in_commissioner)
        }
        
        print(f"  Voted: {total_voted:,} ({turnout_pct:.1f}%)")
        print(f"    Early Voting: {voted_early:,}")
        print(f"    Election Day: {voted_election_day:,}")
        print(f"  Party: DEM={dem:,}, REP={rep:,}")
    
    cur.close()
    return stats


def update_district_counts_cache(stats):
    """
    Update the district_counts_cache table with correct commissioner precinct counts.
    """
    
    print("\n" + "="*80)
    print("UPDATING DISTRICT CACHE")
    print("="*80)
    
    cur = conn.cursor()
    
    for commissioner_id, data in stats.items():
        # Delete existing cache entry
        cur.execute("""
            DELETE FROM district_counts_cache
            WHERE district_id = ?
            AND county = ?
            AND year = ?
        """, (commissioner_id, COUNTY, YEAR))
        
        deleted = cur.rowcount
        if deleted > 0:
            print(f"\n{commissioner_id}: Deleted {deleted} old cache entries")
        
        # Insert new cache entry (SQLite uses datetime('now') instead of NOW())
        cur.execute("""
            INSERT INTO district_counts_cache (
                district_id,
                district_type,
                county,
                year,
                total_voters,
                voted,
                not_voted,
                turnout_percentage,
                dem_votes,
                rep_votes,
                cached_at
            ) VALUES (
                ?, 'commissioner', ?, ?,
                ?, ?, ?, ?, ?, ?,
                datetime('now')
            )
        """, (
            commissioner_id,
            COUNTY,
            YEAR,
            data['total_voters'],
            data['voted'],
            data['not_voted'],
            data['turnout_pct'],
            data['dem'],
            data['rep']
        ))
        
        print(f"{commissioner_id}: Inserted new cache entry")
        print(f"  Total: {data['total_voters']:,}, Voted: {data['voted']:,}, DEM: {data['dem']:,}, REP: {data['rep']:,}")
    
    conn.commit()
    cur.close()
    
    print("\n" + "="*80)
    print("CACHE UPDATE COMPLETE")
    print("="*80)


def verify_results():
    """
    Verify the updated cache entries.
    """
    
    print("\n" + "="*80)
    print("VERIFICATION")
    print("="*80)
    
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            district_id,
            total_voters,
            voted,
            turnout_percentage,
            dem_votes,
            rep_votes,
            cached_at
        FROM district_counts_cache
        WHERE district_type = 'commissioner'
        AND county = ?
        AND year = ?
        ORDER BY district_id
    """, (COUNTY, YEAR))
    
    results = cur.fetchall()
    
    if not results:
        print("\n⚠ No commissioner precinct cache entries found!")
        return
    
    print(f"\nFound {len(results)} commissioner precinct cache entries:\n")
    
    for row in results:
        district_id = row['district_id']
        total = row['total_voters']
        voted = row['voted']
        turnout = row['turnout_percentage']
        dem = row['dem_votes']
        rep = row['rep_votes']
        cached_at = row['cached_at']
        
        print(f"{district_id}:")
        print(f"  Total Voters: {total:,}")
        print(f"  Voted: {voted:,} ({turnout:.1f}%)")
        print(f"  DEM: {dem:,}, REP: {rep:,}")
        if dem + rep > 0:
            dem_pct = dem / (dem + rep) * 100
            print(f"  DEM Share: {dem_pct:.1f}%")
        print(f"  Cached: {cached_at}")
        print()
    
    cur.close()


if __name__ == "__main__":
    print("="*80)
    print("COMMISSIONER PRECINCT VOTE COUNT FIX")
    print("="*80)
    print(f"\nCounty: {COUNTY}")
    print(f"Year: {YEAR}")
    print(f"Election Date: {ELECTION_DATE}")
    
    try:
        # Step 1: Map voting precincts to commissioner precincts
        precinct_mapping = get_precinct_to_commissioner_mapping()
        
        # Step 2: Calculate statistics for each commissioner precinct
        stats = get_commissioner_precinct_stats(precinct_mapping)
        
        # Step 3: Update district cache
        update_district_counts_cache(stats)
        
        # Step 4: Verify results
        verify_results()
        
        print("\n" + "="*80)
        print("✓ COMMISSIONER PRECINCT COUNTS HAVE BEEN CORRECTED!")
        print("="*80)
        print("\nThe counts now reflect only voters in precincts within each")
        print("commissioner precinct, using the same logic as TX-15 district assignment.")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
    
    finally:
        conn.close()
