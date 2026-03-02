"""
Campaign Reports Module
Generates actionable intelligence reports for campaigns
"""
import sqlite3
from datetime import datetime


def get_precinct_performance(conn, county, election_date):
    """
    Generate precinct performance report showing turnout rankings.
    
    Returns list of precincts with:
    - Precinct ID
    - Registered voters
    - Votes cast
    - Turnout percentage
    - Party breakdown
    """
    # Get all precincts with voter counts
    rows = conn.execute("""
        SELECT 
            v.precinct,
            COUNT(DISTINCT v.vuid) as registered,
            COUNT(DISTINCT CASE WHEN ve.vuid IS NOT NULL THEN ve.vuid END) as voted,
            COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
            COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep
        FROM voters v
        LEFT JOIN voter_elections ve ON v.vuid = ve.vuid 
            AND ve.election_date = ?
            AND ve.party_voted IN ('Democratic', 'Republican')
        WHERE v.county = ?
          AND v.precinct IS NOT NULL
          AND v.precinct != ''
        GROUP BY v.precinct
        HAVING registered > 0
        ORDER BY (CAST(voted AS FLOAT) / registered) DESC
    """, [election_date, county]).fetchall()
    
    precincts = []
    for row in rows:
        voted = row['voted']
        registered = row['registered']
        dem = row['dem']
        rep = row['rep']
        turnout_pct = round((voted / registered * 100), 1) if registered > 0 else 0
        dem_pct = round((dem / (dem + rep) * 100), 1) if (dem + rep) > 0 else 0
        
        precincts.append({
            'precinct': row['precinct'],
            'registered': registered,
            'voted': voted,
            'turnout_pct': turnout_pct,
            'dem': dem,
            'rep': rep,
            'dem_pct': dem_pct
        })
    
    return precincts


def get_party_switchers(conn, county, election_date, direction='both'):
    """
    Generate party switchers report with full contact information.
    
    Returns list of voters who changed party affiliation with:
    - Name
    - Address
    - Precinct
    - Previous party
    - Current party
    - Age
    """
    # Find voters who switched parties
    query = """
        SELECT 
            v.first_name || ' ' || v.last_name as name,
            v.address,
            v.precinct,
            ve_prev.party_voted as from_party,
            ve_cur.party_voted as to_party,
            (? - v.birth_year) as age
        FROM voter_elections ve_cur
        JOIN voters v ON ve_cur.vuid = v.vuid
        JOIN voter_elections ve_prev ON ve_cur.vuid = ve_prev.vuid
        WHERE ve_cur.election_date = ?
          AND v.county = ?
          AND ve_prev.election_date = (
              SELECT MAX(ve2.election_date)
              FROM voter_elections ve2
              WHERE ve2.vuid = ve_cur.vuid
                AND ve2.election_date < ?
                AND ve2.party_voted IN ('Democratic', 'Republican')
          )
          AND ve_cur.party_voted != ve_prev.party_voted
          AND ve_cur.party_voted IN ('Democratic', 'Republican')
          AND ve_prev.party_voted IN ('Democratic', 'Republican')
    """
    
    params = [datetime.now().year, election_date, county, election_date]
    
    if direction == 'd2r':
        query += " AND ve_prev.party_voted = 'Democratic' AND ve_cur.party_voted = 'Republican'"
    elif direction == 'r2d':
        query += " AND ve_prev.party_voted = 'Republican' AND ve_cur.party_voted = 'Democratic'"
    
    query += " ORDER BY v.precinct, v.last_name"
    
    rows = conn.execute(query, params).fetchall()
    
    switchers = []
    d2r_count = 0
    r2d_count = 0
    
    for row in rows:
        switcher = {
            'name': row['name'],
            'address': row['address'] or 'N/A',
            'precinct': row['precinct'] or 'N/A',
            'from_party': row['from_party'],
            'to_party': row['to_party'],
            'age': row['age'] if row['age'] and row['age'] > 0 else None
        }
        switchers.append(switcher)
        
        if row['from_party'] == 'Democratic':
            d2r_count += 1
        else:
            r2d_count += 1
    
    return {
        'switchers': switchers,
        'd2r': d2r_count,
        'r2d': r2d_count
    }


def get_non_voters(conn, county, precinct='all', history='all'):
    """
    Generate turf cuts report of registered non-voters.
    
    Returns list of registered voters who didn't vote with:
    - Name
    - Address
    - Precinct
    - Last voted date
    - Voting history score
    - Age
    """
    query = """
        SELECT 
            v.first_name || ' ' || v.last_name as name,
            v.address,
            v.precinct,
            (SELECT MAX(ve2.election_date) 
             FROM voter_elections ve2 
             WHERE ve2.vuid = v.vuid 
               AND ve2.party_voted IN ('Democratic', 'Republican')) as last_voted,
            (SELECT COUNT(DISTINCT ve2.election_date)
             FROM voter_elections ve2
             WHERE ve2.vuid = v.vuid
               AND ve2.party_voted IN ('Democratic', 'Republican')) as vote_count,
            (? - v.birth_year) as age
        FROM voters v
        WHERE v.county = ?
          AND NOT EXISTS (
              SELECT 1 FROM voter_elections ve
              WHERE ve.vuid = v.vuid
                AND ve.election_date = ?
                AND ve.party_voted IN ('Democratic', 'Republican')
          )
    """
    
    params = [datetime.now().year, county]
    
    # Add precinct filter
    if precinct != 'all':
        query += " AND v.precinct = ?"
        params.append(precinct)
    
    # Note: We'll filter by history after fetching since it requires the vote_count
    query += " ORDER BY v.precinct, v.last_name LIMIT 5000"
    
    rows = conn.execute(query, params).fetchall()
    
    non_voters = []
    for row in rows:
        vote_count = row['vote_count'] or 0
        
        # Apply history filter
        if history == 'never' and vote_count > 0:
            continue
        elif history == 'sporadic' and (vote_count == 0 or vote_count > 5):
            continue
        
        # Calculate voting score (0-10 based on participation)
        voting_score = min(10, vote_count * 2)
        
        non_voters.append({
            'name': row['name'],
            'address': row['address'] or 'N/A',
            'precinct': row['precinct'] or 'N/A',
            'last_voted': row['last_voted'] or 'Never',
            'voting_score': voting_score,
            'age': row['age'] if row['age'] and row['age'] > 0 else None
        })
    
    return non_voters


def get_new_voters(conn, county, election_date, party='both'):
    """
    Generate new voters report - first-time primary voters.
    
    Returns list of voters with no prior primary voting history:
    - Name
    - Address
    - Precinct
    - Party voted
    - Age
    - Registration date
    """
    query = """
        SELECT 
            v.first_name || ' ' || v.last_name as name,
            v.address,
            v.precinct,
            ve.party_voted as party,
            (? - v.birth_year) as age,
            v.registration_date
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ?
          AND v.county = ?
          AND ve.party_voted IN ('Democratic', 'Republican')
          AND NOT EXISTS (
              SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid
                AND ve2.election_date < ?
                AND ve2.party_voted IN ('Democratic', 'Republican')
          )
    """
    
    params = [datetime.now().year, election_date, county, election_date]
    
    if party != 'both':
        query += " AND ve.party_voted = ?"
        params.append(party)
    
    query += " ORDER BY v.precinct, v.last_name"
    
    rows = conn.execute(query, params).fetchall()
    
    new_voters = []
    dem_count = 0
    rep_count = 0
    
    for row in rows:
        voter = {
            'name': row['name'],
            'address': row['address'] or 'N/A',
            'precinct': row['precinct'] or 'N/A',
            'party': row['party'],
            'age': row['age'] if row['age'] and row['age'] > 0 else None,
            'registration_date': row['registration_date'] or 'N/A'
        }
        new_voters.append(voter)
        
        if row['party'] == 'Democratic':
            dem_count += 1
        else:
            rep_count += 1
    
    return {
        'new_voters': new_voters,
        'dem_count': dem_count,
        'rep_count': rep_count
    }
