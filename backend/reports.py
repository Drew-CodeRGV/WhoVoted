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
            v.firstname || ' ' || v.lastname as name,
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
    
    query += " ORDER BY v.precinct, v.lastname"
    
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


def get_non_voters(conn, county, election_date, precinct='all', history='all', party_affinity='all', sort_by='precinct'):
    """
    Generate turf cuts report of registered non-voters.
    
    Returns list of registered voters who didn't vote with:
    - Name
    - Address
    - Precinct
    - Last voted date
    - Voting history score
    - Age
    - Party affinity (based on voting history)
    - Coordinates for mapping
    
    sort_by options: 'precinct', 'turnout_asc', 'turnout_desc'
    """
    # First, get precinct turnout data if sorting by turnout
    precinct_turnout = {}
    if sort_by in ['turnout_asc', 'turnout_desc']:
        turnout_rows = conn.execute("""
            SELECT 
                v.precinct,
                COUNT(DISTINCT v.vuid) as registered,
                COUNT(DISTINCT CASE WHEN ve.vuid IS NOT NULL THEN ve.vuid END) as voted
            FROM voters v
            LEFT JOIN voter_elections ve ON v.vuid = ve.vuid 
                AND ve.election_date = ?
                AND ve.party_voted IN ('Democratic', 'Republican')
            WHERE v.county = ?
              AND v.precinct IS NOT NULL
              AND v.precinct != ''
            GROUP BY v.precinct
        """, [election_date, county]).fetchall()
        
        for row in turnout_rows:
            registered = row['registered']
            voted = row['voted']
            turnout_pct = (voted / registered * 100) if registered > 0 else 0
            precinct_turnout[row['precinct']] = {
                'registered': registered,
                'voted': voted,
                'turnout_pct': round(turnout_pct, 1)
            }
    
    query = """
        SELECT 
            v.vuid,
            v.firstname || ' ' || v.lastname as name,
            v.address,
            v.precinct,
            v.lat,
            v.lng,
            (SELECT MAX(ve2.election_date) 
             FROM voter_elections ve2 
             WHERE ve2.vuid = v.vuid 
               AND ve2.party_voted IN ('Democratic', 'Republican')) as last_voted,
            (SELECT COUNT(DISTINCT ve2.election_date)
             FROM voter_elections ve2
             WHERE ve2.vuid = v.vuid
               AND ve2.party_voted IN ('Democratic', 'Republican')) as vote_count,
            (SELECT COUNT(DISTINCT ve2.election_date)
             FROM voter_elections ve2
             WHERE ve2.vuid = v.vuid
               AND ve2.party_voted = 'Democratic') as dem_count,
            (SELECT COUNT(DISTINCT ve2.election_date)
             FROM voter_elections ve2
             WHERE ve2.vuid = v.vuid
               AND ve2.party_voted = 'Republican') as rep_count,
            (? - v.birth_year) as age
        FROM voters v
        WHERE v.county = ?
          AND v.geocoded = 1
          AND NOT EXISTS (
              SELECT 1 FROM voter_elections ve
              WHERE ve.vuid = v.vuid
                AND ve.election_date = ?
                AND ve.party_voted IN ('Democratic', 'Republican')
          )
    """
    
    params = [datetime.now().year, county, election_date]
    
    # Add precinct filter
    if precinct != 'all':
        query += " AND v.precinct = ?"
        params.append(precinct)
    
    # Add party affinity filter
    if party_affinity == 'democratic':
        query += """ AND EXISTS (
            SELECT 1 FROM voter_elections ve3
            WHERE ve3.vuid = v.vuid
              AND ve3.party_voted = 'Democratic'
        )"""
    elif party_affinity == 'republican':
        query += """ AND EXISTS (
            SELECT 1 FROM voter_elections ve3
            WHERE ve3.vuid = v.vuid
              AND ve3.party_voted = 'Republican'
        )"""
    
    # Note: We'll filter by history after fetching since it requires the vote_count
    query += " ORDER BY v.precinct, v.lastname LIMIT 5000"
    
    rows = conn.execute(query, params).fetchall()
    
    non_voters = []
    for row in rows:
        vote_count = row['vote_count'] or 0
        dem_count = row['dem_count'] or 0
        rep_count = row['rep_count'] or 0
        
        # Apply history filter
        if history == 'never' and vote_count > 0:
            continue
        elif history == 'sporadic' and (vote_count == 0 or vote_count > 5):
            continue
        
        # Determine party affinity
        if dem_count > rep_count:
            affinity = 'Democratic'
        elif rep_count > dem_count:
            affinity = 'Republican'
        elif dem_count > 0 and rep_count > 0:
            affinity = 'Mixed'
        else:
            affinity = 'Unknown'
        
        # Calculate voting score (0-10 based on participation)
        voting_score = min(10, vote_count * 2)
        
        voter_precinct = row['precinct'] or 'N/A'
        turnout_data = precinct_turnout.get(voter_precinct, {})
        
        non_voters.append({
            'vuid': row['vuid'],
            'name': row['name'],
            'address': row['address'] or 'N/A',
            'precinct': voter_precinct,
            'precinct_turnout': turnout_data.get('turnout_pct', 0),
            'precinct_registered': turnout_data.get('registered', 0),
            'precinct_voted': turnout_data.get('voted', 0),
            'last_voted': row['last_voted'] or 'Never',
            'voting_score': voting_score,
            'age': row['age'] if row['age'] and row['age'] > 0 else None,
            'party_affinity': affinity,
            'dem_history': dem_count,
            'rep_history': rep_count,
            'lat': row['lat'],
            'lng': row['lng']
        })
    
    # Sort based on sort_by parameter
    if sort_by == 'turnout_asc':
        non_voters.sort(key=lambda x: (x['precinct_turnout'], x['precinct'], x['name']))
    elif sort_by == 'turnout_desc':
        non_voters.sort(key=lambda x: (-x['precinct_turnout'], x['precinct'], x['name']))
    else:
        non_voters.sort(key=lambda x: (x['precinct'], x['name']))
    
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
            v.firstname || ' ' || v.lastname as name,
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
    
    query += " ORDER BY v.precinct, v.lastname"
    
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



def generate_county_report_data(county: str, election_date: str, voting_method: str = '') -> dict:
    """Generate county report data for caching.
    
    This is the same logic as the /api/county-report endpoint but returns
    the data dict instead of a Flask response.
    """
    import database as db
    
    conn = db.get_connection()
    
    # Build WHERE clause
    where_base = "WHERE v.county = ? AND ve.election_date = ?"
    params_base = [county, election_date]
    if voting_method:
        where_base += " AND ve.voting_method = ?"
        params_base.append(voting_method)
    
    # Total voters
    total_voters = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base}
    """, params_base).fetchone()[0]
    
    # Party breakdown
    dem_count = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND ve.party_voted = 'Democratic'
    """, params_base).fetchone()[0]
    
    rep_count = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND ve.party_voted = 'Republican'
    """, params_base).fetchone()[0]
    
    # Party switchers
    flip_rows = conn.execute(f"""
        SELECT ve_current.party_voted as to_p, ve_prev.party_voted as from_p, COUNT(*) as cnt
        FROM voter_elections ve_current
        JOIN voters v ON ve_current.vuid = v.vuid
        JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
        WHERE v.county = ? AND ve_current.election_date = ?
            AND ve_prev.election_date = (
                SELECT MAX(ve2.election_date) FROM voter_elections ve2
                WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
            AND ve_current.party_voted != ve_prev.party_voted
            AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
        GROUP BY ve_current.party_voted, ve_prev.party_voted
    """, [county, election_date]).fetchall()
    
    r2d = sum(r[2] for r in flip_rows if r[1] == 'Republican' and r[0] == 'Democratic')
    d2r = sum(r[2] for r in flip_rows if r[1] == 'Democratic' and r[0] == 'Republican')
    
    # New voters
    new_voters = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base}
          AND EXISTS (SELECT 1 FROM voter_elections ve_prior
              JOIN voters v2 ON ve_prior.vuid = v2.vuid
              WHERE v2.county = v.county AND ve_prior.election_date < ?
                AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
              LIMIT 1)
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    """, params_base + [election_date, election_date]).fetchone()[0]
    
    new_dem = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND ve.party_voted = 'Democratic'
          AND EXISTS (SELECT 1 FROM voter_elections ve_prior
              JOIN voters v2 ON ve_prior.vuid = v2.vuid
              WHERE v2.county = v.county AND ve_prior.election_date < ?
                AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
              LIMIT 1)
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    """, params_base + [election_date, election_date]).fetchone()[0]
    
    new_rep = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND ve.party_voted = 'Republican'
          AND EXISTS (SELECT 1 FROM voter_elections ve_prior
              JOIN voters v2 ON ve_prior.vuid = v2.vuid
              WHERE v2.county = v.county AND ve_prior.election_date < ?
                AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
              LIMIT 1)
          AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
              WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
    """, params_base + [election_date, election_date]).fetchone()[0]
    
    # Gender
    female_count = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND v.sex = 'F'
    """, params_base).fetchone()[0]
    
    male_count = conn.execute(f"""
        SELECT COUNT(*) FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base} AND v.sex = 'M'
    """, params_base).fetchone()[0]
    
    # Age groups
    age_rows = conn.execute(f"""
        SELECT
            CASE
                WHEN v.birth_year BETWEEN 2002 AND 2008 THEN '18-24'
                WHEN v.birth_year BETWEEN 1992 AND 2001 THEN '25-34'
                WHEN v.birth_year BETWEEN 1982 AND 1991 THEN '35-44'
                WHEN v.birth_year BETWEEN 1972 AND 1981 THEN '45-54'
                WHEN v.birth_year BETWEEN 1962 AND 1971 THEN '55-64'
                WHEN v.birth_year BETWEEN 1952 AND 1961 THEN '65-74'
                WHEN v.birth_year > 0 AND v.birth_year < 1952 THEN '75+'
                ELSE 'Unknown'
            END as age_group,
            ve.party_voted,
            COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        {where_base}
        GROUP BY age_group, ve.party_voted
    """, params_base).fetchall()
    
    age_groups = {}
    for row in age_rows:
        ag, party, cnt = row[0], row[1], row[2]
        if ag not in age_groups:
            age_groups[ag] = {'total': 0, 'dem': 0, 'rep': 0}
        age_groups[ag]['total'] += cnt
        if party == 'Democratic':
            age_groups[ag]['dem'] += cnt
        elif party == 'Republican':
            age_groups[ag]['rep'] += cnt
    
    # Calculate percentages
    dem_share = round(dem_count / (dem_count + rep_count) * 100, 1) if (dem_count + rep_count) else 0
    new_dem_pct = round(new_dem / new_voters * 100, 1) if new_voters else 0
    female_pct = round(female_count / (female_count + male_count) * 100, 1) if (female_count + male_count) else 0
    
    return {
        'county': county,
        'election_date': election_date,
        'voting_method': voting_method or 'all',
        'total_voters': total_voters,
        'dem_count': dem_count,
        'rep_count': rep_count,
        'dem_share': dem_share,
        'r2d': r2d,
        'd2r': d2r,
        'new_voters': new_voters,
        'new_dem': new_dem,
        'new_rep': new_rep,
        'new_dem_pct': new_dem_pct,
        'female_count': female_count,
        'male_count': male_count,
        'female_pct': female_pct,
        'age_groups': age_groups,
        'last_updated': election_date
    }
