#!/usr/bin/env python3
"""
API endpoints for HD-41 Runoff Election tracking.
Dem: Salinas vs Haddad | Rep: Sanchez vs Groves | May 26, 2026
"""

from flask import Blueprint, jsonify
import sqlite3
from datetime import datetime

bp = Blueprint('hd41', __name__, url_prefix='/api/hd41')

DB_PATH = '/opt/whovoted/data/whovoted.db'
ELECTION_DATE = '2026-05-26'
DISTRICT = 'HD-41'


@bp.route('/stats')
def get_stats():
    """Get overall statistics for HD-41 runoff."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    total = conn.execute("""
        SELECT COUNT(DISTINCT ve.vuid) as total
        FROM voter_elections ve
        INNER JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ? AND v.state_house_district = ?
    """, (ELECTION_DATE, DISTRICT)).fetchone()['total']

    # Party breakdown
    party_rows = conn.execute("""
        SELECT ve.party_voted, COUNT(DISTINCT ve.vuid) as cnt
        FROM voter_elections ve
        INNER JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ? AND v.state_house_district = ?
        GROUP BY ve.party_voted
    """, (ELECTION_DATE, DISTRICT)).fetchall()
    parties = {r['party_voted']: r['cnt'] for r in party_rows if r['party_voted']}

    # Precinct breakdown
    precinct_rows = conn.execute("""
        SELECT v.precinct, AVG(v.lat) as lat, AVG(v.lng) as lng,
               COUNT(DISTINCT ve.vuid) as voters
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE ve.election_date = ? AND v.state_house_district = ?
        AND v.precinct IS NOT NULL AND v.lat IS NOT NULL
        GROUP BY v.precinct ORDER BY voters DESC
    """, (ELECTION_DATE, DISTRICT)).fetchall()
    precincts = [{'name': r['precinct'], 'lat': r['lat'], 'lng': r['lng'], 'voters': r['voters']} for r in precinct_rows]

    last_update = conn.execute("""
        SELECT MAX(created_at) as lu FROM voter_elections WHERE election_date = ?
    """, (ELECTION_DATE,)).fetchone()['lu'] or datetime.now().isoformat()

    conn.close()

    return jsonify({
        'total_voters': total,
        'parties': parties,
        'precincts_count': len(precincts),
        'precincts': precincts,
        'last_update': last_update,
        'candidates': {
            'Democratic': 'Julio Salinas vs. Victor "Seby" Haddad',
            'Republican': 'Sergio Sanchez vs. Gary Groves'
        }
    })


@bp.route('/precinct/<precinct_id>')
def get_precinct_detail(precinct_id):
    """Get detailed information for a specific precinct."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    row = conn.execute("""
        SELECT
            COUNT(DISTINCT ve.vuid) as total_voters,
            COUNT(DISTINCT CASE WHEN ve.voting_method = 'early-voting' THEN ve.vuid END) as early_voters,
            COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
            COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep
        FROM voters v
        INNER JOIN voter_elections ve ON v.vuid = ve.vuid
        WHERE v.precinct = ? AND ve.election_date = ? AND v.state_house_district = ?
    """, (precinct_id, ELECTION_DATE, DISTRICT)).fetchone()

    conn.close()

    return jsonify({
        'precinct': precinct_id,
        'total_voters': row['total_voters'],
        'early_voters': row['early_voters'],
        'dem': row['dem'],
        'rep': row['rep']
    })
