"""
District 15 Election Night Dashboard Backend
Separate from main Politiquera site
"""

from flask import Flask, jsonify, request
from functools import wraps
import sqlite3
import logging
import os

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-key-change-in-production')

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database path
DB_PATH = '/opt/whovoted/data/d15_elections.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def require_auth(f):
    """Simple auth decorator - checks for admin session"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # For now, allow all requests - add proper auth later
        return f(*args, **kwargs)
    return decorated_function

@app.route('/d15api/results')
def d15_results():
    """Get real-time election results for District 15."""
    try:
        conn = get_db()
        
        # Create table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS d15_election_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                election_date TEXT NOT NULL,
                district TEXT NOT NULL,
                county TEXT NOT NULL,
                precinct TEXT NOT NULL,
                bobby_early INTEGER DEFAULT 0,
                bobby_election INTEGER DEFAULT 0,
                bobby_absentee INTEGER DEFAULT 0,
                bobby_total INTEGER DEFAULT 0,
                ada_early INTEGER DEFAULT 0,
                ada_election INTEGER DEFAULT 0,
                ada_absentee INTEGER DEFAULT 0,
                ada_total INTEGER DEFAULT 0,
                dem_votes INTEGER DEFAULT 0,
                rep_votes INTEGER DEFAULT 0,
                updated_at TEXT,
                UNIQUE(election_date, district, county, precinct)
            )
        """)
        conn.commit()
        
        # Get the most recent election date with results
        latest_election = conn.execute("""
            SELECT election_date FROM d15_election_results
            ORDER BY election_date DESC, updated_at DESC
            LIMIT 1
        """).fetchone()
        
        if not latest_election:
            return jsonify({
                'totals': {'bobby': 0, 'ada': 0, 'dem': 0, 'rep': 0},
                'counties': [],
                'precincts': []
            })
        
        election_date = latest_election[0]
        
        # Get district-wide totals with breakdowns
        totals = conn.execute("""
            SELECT 
                SUM(bobby_total) as bobby_total,
                SUM(bobby_early) as bobby_early,
                SUM(bobby_election) as bobby_election,
                SUM(bobby_absentee) as bobby_absentee,
                SUM(ada_total) as ada_total,
                SUM(ada_early) as ada_early,
                SUM(ada_election) as ada_election,
                SUM(ada_absentee) as ada_absentee,
                SUM(dem_votes) as dem,
                SUM(rep_votes) as rep
            FROM d15_election_results
            WHERE election_date = ? AND district = '15'
        """, [election_date]).fetchone()
        
        # Get county breakdowns with details
        counties = conn.execute("""
            SELECT 
                county,
                SUM(bobby_total) as bobby_total,
                SUM(bobby_early) as bobby_early,
                SUM(bobby_election) as bobby_election,
                SUM(bobby_absentee) as bobby_absentee,
                SUM(ada_total) as ada_total,
                SUM(ada_early) as ada_early,
                SUM(ada_election) as ada_election,
                SUM(ada_absentee) as ada_absentee,
                SUM(dem_votes) as dem,
                SUM(rep_votes) as rep
            FROM d15_election_results
            WHERE election_date = ? AND district = '15'
            GROUP BY county
            ORDER BY (bobby_total + ada_total) DESC
        """, [election_date]).fetchall()
        
        # Get precinct breakdowns with details
        precincts = conn.execute("""
            SELECT 
                county,
                precinct,
                bobby_total,
                bobby_early,
                bobby_election,
                bobby_absentee,
                ada_total,
                ada_early,
                ada_election,
                ada_absentee,
                dem_votes as dem,
                rep_votes as rep
            FROM d15_election_results
            WHERE election_date = ? AND district = '15'
            ORDER BY (bobby_total + ada_total) DESC
        """, [election_date]).fetchall()
        
        return jsonify({
            'totals': {
                'bobby': totals[0] or 0,
                'bobby_early': totals[1] or 0,
                'bobby_election': totals[2] or 0,
                'bobby_absentee': totals[3] or 0,
                'ada': totals[4] or 0,
                'ada_early': totals[5] or 0,
                'ada_election': totals[6] or 0,
                'ada_absentee': totals[7] or 0,
                'dem': totals[8] or 0,
                'rep': totals[9] or 0
            },
            'counties': [
                {
                    'name': row[0],
                    'bobby': row[1] or 0,
                    'bobby_early': row[2] or 0,
                    'bobby_election': row[3] or 0,
                    'bobby_absentee': row[4] or 0,
                    'ada': row[5] or 0,
                    'ada_early': row[6] or 0,
                    'ada_election': row[7] or 0,
                    'ada_absentee': row[8] or 0,
                    'dem': row[9] or 0,
                    'rep': row[10] or 0
                }
                for row in counties
            ],
            'precincts': [
                {
                    'county': row[0],
                    'number': row[1],
                    'bobby': row[2] or 0,
                    'bobby_early': row[3] or 0,
                    'bobby_election': row[4] or 0,
                    'bobby_absentee': row[5] or 0,
                    'ada': row[6] or 0,
                    'ada_early': row[7] or 0,
                    'ada_election': row[8] or 0,
                    'ada_absentee': row[9] or 0,
                    'dem': row[10] or 0,
                    'rep': row[11] or 0
                }
                for row in precincts
            ]
        })
        
    except Exception as e:
        logger.error(f"Error fetching D15 results: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/d15api/upload', methods=['POST'])
@require_auth
def d15_upload_results():
    """Upload election results for District 15.
    
    Expects JSON with results array containing detailed breakdowns per precinct.
    Bobby Pulido = dem_votes (blue), Ada Cuellar = rep_votes (orange)
    """
    try:
        from datetime import datetime
        
        data = request.get_json()
        if not data or 'results' not in data:
            return jsonify({'error': 'No results data provided'}), 400
        
        results = data['results']
        if not isinstance(results, list) or len(results) == 0:
            return jsonify({'error': 'Results must be a non-empty array'}), 400
        
        conn = get_db()
        election_date = datetime.now().strftime('%Y-%m-%d')
        updated_at = datetime.now().isoformat()
        
        # Create table if it doesn't exist
        conn.execute("""
            CREATE TABLE IF NOT EXISTS d15_election_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                election_date TEXT NOT NULL,
                district TEXT NOT NULL,
                county TEXT NOT NULL,
                precinct TEXT NOT NULL,
                bobby_early INTEGER DEFAULT 0,
                bobby_election INTEGER DEFAULT 0,
                bobby_absentee INTEGER DEFAULT 0,
                bobby_total INTEGER DEFAULT 0,
                ada_early INTEGER DEFAULT 0,
                ada_election INTEGER DEFAULT 0,
                ada_absentee INTEGER DEFAULT 0,
                ada_total INTEGER DEFAULT 0,
                dem_votes INTEGER DEFAULT 0,
                rep_votes INTEGER DEFAULT 0,
                updated_at TEXT,
                UNIQUE(election_date, district, county, precinct)
            )
        """)
        
        count = 0
        for row in results:
            precinct = str(row.get('precinct', '')).strip()
            county = str(row.get('county', 'Unknown')).strip()
            
            # Get detailed breakdowns if available, otherwise use totals
            bobby_early = int(row.get('bobby_early', 0) or 0)
            bobby_election = int(row.get('bobby_election', 0) or 0)
            bobby_absentee = int(row.get('bobby_absentee', 0) or 0)
            bobby_total = int(row.get('bobby_votes', 0) or 0)
            
            ada_early = int(row.get('ada_early', 0) or 0)
            ada_election = int(row.get('ada_election', 0) or 0)
            ada_absentee = int(row.get('ada_absentee', 0) or 0)
            ada_total = int(row.get('ada_votes', 0) or 0)
            
            # If total not provided, calculate from breakdowns
            if bobby_total == 0 and (bobby_early + bobby_election + bobby_absentee) > 0:
                bobby_total = bobby_early + bobby_election + bobby_absentee
            if ada_total == 0 and (ada_early + ada_election + ada_absentee) > 0:
                ada_total = ada_early + ada_election + ada_absentee
            
            if not precinct or county == 'Unknown':
                logger.warning(f"Skipping precinct {precinct} - missing county mapping")
                continue
            
            # Bobby = dem_votes (blue), Ada = rep_votes (orange)
            conn.execute("""
                INSERT INTO d15_election_results 
                (election_date, district, county, precinct, 
                 bobby_early, bobby_election, bobby_absentee, bobby_total,
                 ada_early, ada_election, ada_absentee, ada_total,
                 dem_votes, rep_votes, updated_at)
                VALUES (?, '15', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(election_date, district, county, precinct) 
                DO UPDATE SET
                    bobby_early = excluded.bobby_early,
                    bobby_election = excluded.bobby_election,
                    bobby_absentee = excluded.bobby_absentee,
                    bobby_total = excluded.bobby_total,
                    ada_early = excluded.ada_early,
                    ada_election = excluded.ada_election,
                    ada_absentee = excluded.ada_absentee,
                    ada_total = excluded.ada_total,
                    dem_votes = excluded.dem_votes,
                    rep_votes = excluded.rep_votes,
                    updated_at = excluded.updated_at
            """, [election_date, county, precinct, 
                  bobby_early, bobby_election, bobby_absentee, bobby_total,
                  ada_early, ada_election, ada_absentee, ada_total,
                  bobby_total, ada_total, updated_at])
            count += 1
        
        conn.commit()
        
        logger.info(f"Uploaded {count} election results for District 15")
        return jsonify({'success': True, 'count': count})
        
    except Exception as e:
        logger.error(f"Error uploading D15 results: {e}")
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=False)
