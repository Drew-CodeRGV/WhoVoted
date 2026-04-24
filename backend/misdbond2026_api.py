#!/usr/bin/env python3
"""
API endpoints for McAllen ISD Bond 2026 election tracking.
"""

from flask import Blueprint, jsonify
import sqlite3
from datetime import datetime

bp = Blueprint('misdbond2026', __name__, url_prefix='/api/misdbond2026')

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-05-10'  # McAllen ISD Bond election date

@bp.route('/stats')
def get_stats():
    """Get overall statistics for McAllen ISD Bond election."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    # Get total voters
    cur.execute("""
        SELECT COUNT(DISTINCT ve.vuid) as total
        FROM voter_elections ve
        WHERE ve.election_date = ?
    """, (ELECTION_DATE,))
    
    total_voters = cur.fetchone()['total']
    
    # Get precinct breakdown
    cur.execute("""
        SELECT 
            v.precinct,
            AVG(v.lat) as lat,
            AVG(v.lng) as lng,
            COUNT(DISTINCT ve.vuid) as voters
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ?
        AND v.precinct IS NOT NULL
        AND v.lat IS NOT NULL
        AND v.lng IS NOT NULL
        GROUP BY v.precinct
        ORDER BY voters DESC
    """, (ELECTION_DATE,))
    
    precincts = []
    for row in cur.fetchall():
        precincts.append({
            'name': row['precinct'],
            'lat': row['lat'],
            'lng': row['lng'],
            'voters': row['voters']
        })
    
    # Get last update time
    cur.execute("""
        SELECT MAX(created_at) as last_update
        FROM voter_elections
        WHERE election_date = ?
    """, (ELECTION_DATE,))
    
    last_update_row = cur.fetchone()
    last_update = last_update_row['last_update'] if last_update_row['last_update'] else datetime.now().isoformat()
    
    conn.close()
    
    return jsonify({
        'total_voters': total_voters,
        'precincts_count': len(precincts),
        'precincts': precincts,
        'last_update': last_update
    })

@bp.route('/precinct/<precinct_id>')
def get_precinct_detail(precinct_id):
    """Get detailed information for a specific precinct."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    
    cur.execute("""
        SELECT 
            COUNT(DISTINCT ve.vuid) as total_voters,
            COUNT(DISTINCT CASE WHEN ve.voting_method = 'early-voting' THEN ve.vuid END) as early_voters
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.precinct = ? AND ve.election_date = ?
    """, (precinct_id, ELECTION_DATE))
    
    row = cur.fetchone()
    conn.close()
    
    return jsonify({
        'precinct': precinct_id,
        'total_voters': row['total_voters'],
        'early_voters': row['early_voters']
    })
