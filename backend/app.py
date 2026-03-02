"""Main Flask application for WhoVoted backend."""
from flask import Flask, request, jsonify, send_from_directory, redirect, make_response
from flask_cors import CORS
import logging
import threading
import json
import os
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from config import Config, setup_logging
from auth import (create_session, validate_session, invalidate_session,
                 require_auth, require_superadmin, verify_google_token,
                 get_or_create_user, get_session_info, list_users,
                 update_user_role, delete_user, update_user_info)
from upload import validate_file, save_upload, get_file_info, cleanup_old_uploads
from processor import ProcessingJob, CrossReferenceEngine
import database as db

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)
app.config['MAX_CONTENT_LENGTH'] = 250 * 1024 * 1024  # 250MB max upload size

# Validate configuration
Config.validate()

# Setup logging
logger = setup_logging()

# Configure CORS
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

# Initialize database
db.init_db()

# ── Simple in-memory cache for expensive queries ──
import time as _time

_query_cache = {}
_cache_lock = threading.Lock()
CACHE_TTL = 1800  # 30 minutes — data only changes when scraper runs

def cache_get(key):
    with _cache_lock:
        entry = _query_cache.get(key)
        if entry and (_time.time() - entry['ts']) < CACHE_TTL:
            return entry['data']
    return None

def cache_set(key, data):
    with _cache_lock:
        _query_cache[key] = {'data': data, 'ts': _time.time()}

def cache_invalidate():
    """Clear all cached query results (call after data changes)."""
    with _cache_lock:
        _query_cache.clear()
    # Rebuild static cache files in background
    threading.Thread(target=_rebuild_static_cache, name='rebuild-cache', daemon=True).start()
    # Refresh the election summary table in background
    try:
        threading.Thread(target=db.refresh_election_summary, name='refresh_summary', daemon=True).start()
    except Exception:
        pass


def _rebuild_static_cache():
    """Rebuild pre-computed static JSON files for all known datasets.
    
    Called after data changes (uploads, scraper runs). Generates files in
    /opt/whovoted/public/cache/ that the API endpoints serve directly,
    giving instant response times without hitting the DB.
    """
    try:
        logger.info("Rebuilding static cache files...")
        t0 = _time.time()
        cache_dir = '/opt/whovoted/public/cache'
        os.makedirs(cache_dir, exist_ok=True)
        
        # Get all known datasets from election_summary
        conn = db.get_connection()
        try:
            rows = conn.execute("""
                SELECT DISTINCT county, election_date, voting_method
                FROM election_summary
                WHERE election_date IS NOT NULL
                ORDER BY election_date DESC
            """).fetchall()
        except Exception:
            rows = []
        finally:
            conn.close()
        
        # Always include the default dataset
        datasets = set()
        datasets.add(('Hidalgo', '2026-03-03', 'early-voting'))
        for r in rows:
            if r[0] and r[1]:
                datasets.add((r[0], r[1], r[2] or None))
        
        rebuilt = 0
        for county, election_date, voting_method in datasets:
            try:
                method_str = voting_method or 'all'
                
                # Heatmap
                points = db.get_voters_heatmap(county, election_date, voting_method)
                hm_data = json.dumps({'points': points, 'count': len(points)}, separators=(',', ':'))
                hm_path = os.path.join(cache_dir, f'heatmap_{county}_{election_date}_{method_str}.json')
                with open(hm_path, 'w') as f:
                    f.write(hm_data)
                
                # Stats
                stats = db.get_election_stats(county, election_date, None, voting_method)
                stats_data = json.dumps({'success': True, 'stats': stats}, separators=(',', ':'))
                stats_path = os.path.join(cache_dir, f'stats_{county}_{election_date}_{method_str}.json')
                with open(stats_path, 'w') as f:
                    f.write(stats_data)
                
                rebuilt += 1
            except Exception as e:
                logger.warning(f"Failed to rebuild cache for {county}/{election_date}/{voting_method}: {e}")
        
        logger.info(f"Static cache rebuilt: {rebuilt} datasets in {_time.time()-t0:.1f}s")

        # Build county overview cache for each unique election_date + voting_method
        overview_dates = set()
        for _, ed, vm in datasets:
            overview_dates.add((ed, vm))
        for ed, vm in overview_dates:
            try:
                method_str = vm or 'all'
                conn2 = db.get_connection()
                try:
                    where = "WHERE ve.election_date = ? AND ve.party_voted != '' AND ve.party_voted IS NOT NULL"
                    params = [ed]
                    if vm:
                        where += " AND ve.voting_method = ?"
                        params.append(vm)
                    ov_rows = conn2.execute(f"""
                        SELECT v.county,
                               ROUND(AVG(v.lat), 4) as lat,
                               ROUND(AVG(v.lng), 4) as lng,
                               COUNT(DISTINCT ve.vuid) as total,
                               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
                               COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep
                        FROM voter_elections ve
                        JOIN voters v ON ve.vuid = v.vuid
                        {where}
                        AND v.geocoded = 1 AND v.lat IS NOT NULL
                        GROUP BY v.county
                        ORDER BY total DESC
                    """, params).fetchall()
                    counties_data = []
                    for r in ov_rows:
                        if r['county'] and r['lat']:
                            counties_data.append({'county': r['county'], 'lat': r['lat'], 'lng': r['lng'],
                                                  'total': r['total'], 'dem': r['dem'], 'rep': r['rep']})
                    ov_path = os.path.join(cache_dir, f'county_overview_{ed}_{method_str}.json')
                    with open(ov_path, 'w') as f:
                        json.dump({'success': True, 'counties': counties_data}, f, separators=(',', ':'))
                finally:
                    conn2.close()
            except Exception as e:
                logger.warning(f"Failed to build county overview for {ed}/{vm}: {e}")
    except Exception as e:
        logger.error(f"Static cache rebuild failed: {e}")

# Global job tracker - now supports multiple concurrent jobs
active_jobs: Dict[str, ProcessingJob] = {}
job_queue: List[str] = []
jobs_lock = threading.Lock()
max_concurrent_jobs = 3  # Process up to 3 files simultaneously

# Persistent job storage
JOBS_FILE = Config.DATA_DIR / 'processing_jobs.json'

def load_jobs_from_disk():
    """Load job history from disk."""
    if JOBS_FILE.exists():
        try:
            with open(JOBS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load jobs from disk: {e}")
    return {}

def save_jobs_to_disk():
    """Save job history to disk (merge with existing data for cross-worker safety)."""
    try:
        JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Read existing disk data first (other workers may have written jobs)
        existing_data = {}
        if JOBS_FILE.exists():
            try:
                with open(JOBS_FILE, 'r') as f:
                    existing_data = json.load(f)
            except Exception:
                existing_data = {}
        
        # Build current worker's job data
        current_jobs = {}
        with jobs_lock:
            for job_id, job in active_jobs.items():
                cache_hits = job.cache_hits if hasattr(job, 'cache_hits') else 0
                
                current_jobs[job_id] = {
                    'job_id': job.job_id,
                    'status': job.status,
                    'progress': job.progress,
                    'total_records': job.total_records,
                    'processed_records': job.processed_records,
                    'geocoded_count': job.geocoded_count,
                    'failed_count': job.failed_count,
                    'cache_hits': cache_hits,
                    'county': job.county,
                    'year': job.year,
                    'election_type': job.election_type,
                    'election_date': getattr(job, 'election_date', ''),
                    'voting_method': job.voting_method,
                    'primary_party': getattr(job, 'primary_party', ''),
                    'original_filename': job.original_filename,
                    'csv_path': getattr(job, 'csv_path', ''),
                    'max_workers': getattr(job, 'max_workers', 20),
                    'started_at': job.started_at.isoformat() if hasattr(job, 'started_at') and job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if hasattr(job, 'completed_at') and job.completed_at else None,
                    'errors': job.errors[:5] if hasattr(job, 'errors') else [],
                    'log_messages': job.log_messages[-20:] if hasattr(job, 'log_messages') else []
                }
        
        # Merge: current worker's jobs override existing, but keep other workers' jobs
        merged = existing_data.copy()
        merged.update(current_jobs)
        
        # Cleanup: remove completed/failed jobs older than 24 hours
        from datetime import datetime as _dt, timedelta
        cutoff = (_dt.now() - timedelta(hours=24)).isoformat()
        to_remove = []
        for jid, jdata in merged.items():
            if jdata.get('status') in ('completed', 'failed'):
                completed_at = jdata.get('completed_at', '')
                if completed_at and completed_at < cutoff:
                    to_remove.append(jid)
        for jid in to_remove:
            del merged[jid]
        
        with open(JOBS_FILE, 'w') as f:
            json.dump(merged, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to save jobs to disk: {e}")

@app.route('/')
def index():
    """Serve the main public map page."""
    return send_from_directory(Config.PUBLIC_DIR, 'index.html')

@app.route('/api/config')
def client_config():
    """Serve public client configuration (Google Client ID, etc)."""
    return jsonify({
        'google_client_id': Config.GOOGLE_CLIENT_ID,
    })

@app.route('/<path:path>')
def static_files(path):
    """Serve static files from public directory."""
    try:
        return send_from_directory(Config.PUBLIC_DIR, path)
    except:
        return jsonify({'error': 'File not found'}), 404

# Admin authentication routes

# Public API: voter history across all datasets
@app.route('/api/voter-history/<vuid>')
def voter_history(vuid):
    """Look up a voter's party affiliation across all elections by VUID.
    
    Queries the voter_elections DB table directly so each election shows
    the party the voter ACTUALLY voted in (party_voted), not their
    current_party which reflects only the most recent election.
    """
    try:
        vuid = str(vuid).strip()
        if not vuid:
            return jsonify({'error': 'VUID is required'}), 400

        history = []
        voter_elections = db.get_voter_history(vuid)

        for ve in voter_elections:
            party = ve.get('party_voted', '')
            if not party:
                continue
            # Normalize
            pl = party.lower()
            if 'democrat' in pl or pl == 'd' or pl == 'dem':
                party = 'Democratic'
            elif 'republican' in pl or pl == 'r' or pl == 'rep':
                party = 'Republican'

            history.append({
                'year': ve.get('election_year', ''),
                'electionType': ve.get('election_type', ''),
                'electionDate': ve.get('election_date', ''),
                'primaryParty': party,
                'votingMethod': ve.get('voting_method', ''),
                'party': party,
                'isEarlyVoting': 'early' in (ve.get('voting_method', '') or '').lower(),
            })

        # Sort by election date
        history.sort(key=lambda h: h.get('electionDate', ''))

        return jsonify({'vuid': vuid, 'history': history})

    except Exception as e:
        logger.error(f"Voter history lookup failed: {e}")
        return jsonify({'error': str(e)}), 500


# ── DB-driven API endpoints (replace GeoJSON file serving) ──

@app.route('/api/elections')
def api_elections():
    """List available elections from the DB. Replaces metadata file scanning."""
    try:
        county = request.args.get('county')  # Optional — omit to get all counties
        cache_key = f"elections:{county or 'all'}"
        cached = cache_get(cache_key)
        if cached is not None:
            return jsonify(cached)
        datasets = db.get_election_datasets(county if county else None)
        
        # Group by election_date + voting_method to merge DEM/REP and counties
        grouped = {}
        for ds in datasets:
            key = (ds['election_date'], ds['voting_method'])
            if key not in grouped:
                grouped[key] = {
                    'counties': [],
                    'electionDate': ds['election_date'],
                    'electionYear': ds['election_year'],
                    'electionType': ds['election_type'],
                    'votingMethod': ds['voting_method'],
                    'parties': [],
                    'totalVoters': 0,
                    'geocodedCount': 0,
                    'lastUpdated': ds['last_updated'] or '',
                    'countyBreakdown': {},
                }
            g = grouped[key]
            county_name = ds['county'] or 'Unknown'
            if county_name not in g['counties']:
                g['counties'].append(county_name)
            if ds['party_voted'] and ds['party_voted'] not in g['parties']:
                g['parties'].append(ds['party_voted'])
            g['totalVoters'] += ds['total_voters']
            g['geocodedCount'] += ds['geocoded_count']
            if ds['last_updated'] and ds['last_updated'] > g['lastUpdated']:
                g['lastUpdated'] = ds['last_updated']
            # Per-county breakdown
            if county_name not in g['countyBreakdown']:
                g['countyBreakdown'][county_name] = {'totalVoters': 0, 'geocodedCount': 0, 'parties': []}
            cb = g['countyBreakdown'][county_name]
            cb['totalVoters'] += ds['total_voters']
            cb['geocodedCount'] += ds['geocoded_count']
            if ds['party_voted'] and ds['party_voted'] not in cb['parties']:
                cb['parties'].append(ds['party_voted'])
        
        # Backwards compat: set 'county' to first county (or comma-joined) for old code
        for g in grouped.values():
            g['county'] = g['counties'][0] if len(g['counties']) == 1 else ','.join(sorted(g['counties']))
        
        # Sort: most recent date first, then early-voting before mail-in before election-day
        method_order = {'early-voting': 0, 'mail-in': 1, 'election-day': 2}
        result = sorted(grouped.values(), key=lambda x: (-int(x['electionDate'].replace('-', '')), method_order.get(x['votingMethod'], 9)))
        response_data = {'success': True, 'elections': result}
        cache_set(cache_key, response_data)
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Failed to list elections: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/election-stats')
def api_election_stats():
    """Get aggregate stats for an election from the DB."""
    try:
        county_param = request.args.get('county', 'Hidalgo')
        counties = [c.strip() for c in county_param.split(',') if c.strip()]
        election_date = request.args.get('election_date')
        party = request.args.get('party')  # Optional: 'Democratic' or 'Republican'
        voting_method = request.args.get('voting_method')
        
        if not election_date:
            return jsonify({'error': 'election_date is required'}), 400
        
        # Check for pre-built static cache file (fastest path)
        if len(counties) == 1 and not party:
            method_str = voting_method or 'all'
            cache_file = os.path.join('/opt/whovoted/public', 'cache',
                                      f'stats_{counties[0]}_{election_date}_{method_str}.json')
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    return jsonify(json.loads(f.read()))
        
        cache_key = f"stats:{county_param}:{election_date}:{party}:{voting_method}"
        cached = cache_get(cache_key)
        if cached is not None:
            return jsonify(cached)
        
        # Merge stats across counties
        merged = None
        for county in counties:
            stats = db.get_election_stats(county, election_date, party, voting_method)
            if merged is None:
                merged = stats
            else:
                for k, v in stats.items():
                    if isinstance(v, (int, float)):
                        merged[k] = merged.get(k, 0) + v
        
        response_data = {'success': True, 'stats': merged or {}}
        cache_set(cache_key, response_data)
        return jsonify(response_data)
    except Exception as e:
        logger.error(f"Failed to get election stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/voters')
def api_voters():
    """Get voter data for an election from the DB as GeoJSON.
    
    Query params:
        county (required — comma-separated for multiple, e.g. "Hidalgo,Brooks")
        election_date (required)
        party, voting_method (optional filters)
        sw_lat, sw_lng, ne_lat, ne_lng (optional viewport bounds)
        limit (optional, default no limit)
    """
    try:
        county_param = request.args.get('county', 'Hidalgo')
        counties = [c.strip() for c in county_param.split(',') if c.strip()]
        election_date = request.args.get('election_date')
        party = request.args.get('party')
        voting_method = request.args.get('voting_method')
        limit = request.args.get('limit', type=int)
        
        if not election_date:
            return jsonify({'error': 'election_date is required'}), 400
        
        # Parse viewport bounds if provided
        bounds = None
        sw_lat = request.args.get('sw_lat', type=float)
        sw_lng = request.args.get('sw_lng', type=float)
        ne_lat = request.args.get('ne_lat', type=float)
        ne_lng = request.args.get('ne_lng', type=float)
        if all(v is not None for v in [sw_lat, sw_lng, ne_lat, ne_lng]):
            bounds = {'sw_lat': sw_lat, 'sw_lng': sw_lng,
                      'ne_lat': ne_lat, 'ne_lng': ne_lng}
        
        # Server-side cache for full (unbounded) requests
        cache_key = None
        if bounds is None and limit is None:
            cache_key = f"voters:{county_param}:{election_date}:{party}:{voting_method}"
            cached = cache_get(cache_key)
            if cached is not None:
                response = app.response_class(
                    response=cached,
                    status=200,
                    mimetype='application/json'
                )
                response.headers['Cache-Control'] = 'public, max-age=300'
                return response
        
        # Fetch voters for all requested counties and merge
        all_voters = []
        for county in counties:
            voters = db.get_voters_for_election(
                county, election_date, party, voting_method, bounds, limit
            )
            all_voters.extend(voters)
        
        # Build GeoJSON FeatureCollection
        features = []
        for v in all_voters:
            if v['geocoded'] and v['lat'] is not None and v['lng'] is not None:
                geometry = {'type': 'Point', 'coordinates': [v['lng'], v['lat']]}
            else:
                geometry = None
            
            features.append({
                'type': 'Feature',
                'geometry': geometry,
                'properties': {
                    'vuid': v['vuid'],
                    'name': v['name'],
                    'firstname': v['firstname'],
                    'lastname': v['lastname'],
                    'address': v['address'],
                    'precinct': v['precinct'],
                    'sex': v['sex'],
                    'birth_year': v['birth_year'],
                    'county': v.get('county', ''),
                    'party_affiliation_current': v['party_affiliation_current'],
                    'party_affiliation_previous': v['party_affiliation_previous'],
                    'has_switched_parties': v['has_switched_parties'],
                    'is_new_voter': v['is_new_voter'],
                    'unmatched': not v['geocoded'],
                    'voted_in_current_election': True,
                    'is_registered': True,
                },
            })
        
        import json as _json
        json_str = _json.dumps({
            'type': 'FeatureCollection',
            'features': features,
        })
        
        # Cache the serialized JSON for unbounded requests
        if cache_key is not None:
            cache_set(cache_key, json_str)
        
        response = app.response_class(
            response=json_str,
            status=200,
            mimetype='application/json'
        )
        # Browser cache for 5 minutes
        response.headers['Cache-Control'] = 'public, max-age=300'
        return response
    except Exception as e:
        logger.error(f"Failed to get voters: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/voters/heatmap')
def api_voters_heatmap():
    """Lightweight voter data for heatmap rendering — ~90% smaller than full GeoJSON.
    
    Returns a compact array: [[lng, lat, party_code, flags, sex, birth_year], ...]
    party_code: 1=DEM, 2=REP, 0=other
    flags bitmask: bit0=flipped, bit1=new_voter
    """
    try:
        county_param = request.args.get('county', 'Hidalgo')
        counties = [c.strip() for c in county_param.split(',') if c.strip()]
        election_date = request.args.get('election_date')
        voting_method = request.args.get('voting_method')

        if not election_date:
            return jsonify({'error': 'election_date is required'}), 400

        # Check for pre-built static cache file (fastest path)
        if len(counties) == 1:
            method_str = voting_method or 'all'
            cache_file = os.path.join('/opt/whovoted/public', 'cache',
                                      f'heatmap_{counties[0]}_{election_date}_{method_str}.json')
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    json_str = f.read()
                response = app.response_class(response=json_str, status=200, mimetype='application/json')
                response.headers['Cache-Control'] = 'public, max-age=300'
                return response

        cache_key = f"heatmap:{county_param}:{election_date}:{voting_method}"
        cached = cache_get(cache_key)
        if cached is not None:
            response = app.response_class(response=cached, status=200, mimetype='application/json')
            response.headers['Cache-Control'] = 'public, max-age=300'
            return response

        all_points = []
        for county in counties:
            points = db.get_voters_heatmap(county, election_date, voting_method)
            all_points.extend(points)

        import json as _json
        json_str = _json.dumps({'points': all_points, 'count': len(all_points)})
        cache_set(cache_key, json_str)

        response = app.response_class(response=json_str, status=200, mimetype='application/json')
        response.headers['Cache-Control'] = 'public, max-age=300'
        return response
    except Exception as e:
        logger.error(f"Failed to get heatmap data: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/county-center')
def api_county_center():
    """Get the centroid of a county based on average geocoded voter coordinates."""
    county = request.args.get('county', '')
    if not county:
        return jsonify({'error': 'county is required'}), 400
    cache_key = f"county-center:{county}"
    cached = cache_get(cache_key)
    if cached is not None:
        return jsonify(cached)
    try:
        with db.get_db() as conn:
            row = conn.execute(
                "SELECT AVG(lat) as lat, AVG(lng) as lng, COUNT(*) as cnt "
                "FROM voters WHERE county = ? AND geocoded = 1 AND lat IS NOT NULL",
                (county,)
            ).fetchone()
            if row and row['cnt'] > 0:
                result = {'lat': round(row['lat'], 4), 'lng': round(row['lng'], 4), 'count': row['cnt']}
            else:
                result = {'lat': None, 'lng': None, 'count': 0}
        cache_set(cache_key, result)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get county center: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/county-overview')
def api_county_overview():
    """Lightweight county-level vote totals for anonymous users.

    Returns one entry per county with centroid coords and party breakdown
    for a given election. Tiny payload (~1KB) for instant map rendering.
    """
    try:
        election_date = request.args.get('election_date')
        voting_method = request.args.get('voting_method')

        if not election_date:
            return jsonify({'error': 'election_date is required'}), 400

        method_str = voting_method or 'all'

        # Check static cache first
        cache_file = os.path.join('/opt/whovoted/public', 'cache',
                                  f'county_overview_{election_date}_{method_str}.json')
        if os.path.exists(cache_file):
            with open(cache_file, 'r') as f:
                json_str = f.read()
            resp = app.response_class(response=json_str, status=200,
                                      mimetype='application/json')
            resp.headers['Cache-Control'] = 'public, max-age=300'
            return resp

        cache_key = f"county-overview:{election_date}:{voting_method}"
        cached = cache_get(cache_key)
        if cached is not None:
            return jsonify(cached)

        with db.get_db() as conn:
            where = "WHERE ve.election_date = ? AND ve.party_voted != '' AND ve.party_voted IS NOT NULL"
            params = [election_date]
            if voting_method:
                where += " AND ve.voting_method = ?"
                params.append(voting_method)

            rows = conn.execute(f"""
                SELECT v.county,
                       ROUND(AVG(v.lat), 4) as lat,
                       ROUND(AVG(v.lng), 4) as lng,
                       COUNT(DISTINCT ve.vuid) as total,
                       COUNT(DISTINCT CASE WHEN ve.party_voted = 'Democratic' THEN ve.vuid END) as dem,
                       COUNT(DISTINCT CASE WHEN ve.party_voted = 'Republican' THEN ve.vuid END) as rep
                FROM voter_elections ve
                JOIN voters v ON ve.vuid = v.vuid
                {where}
                AND v.geocoded = 1 AND v.lat IS NOT NULL
                GROUP BY v.county
                ORDER BY total DESC
            """, params).fetchall()

            counties = []
            for r in rows:
                if r['county'] and r['lat']:
                    counties.append({
                        'county': r['county'],
                        'lat': r['lat'],
                        'lng': r['lng'],
                        'total': r['total'],
                        'dem': r['dem'],
                        'rep': r['rep'],
                    })

        result = {'success': True, 'counties': counties}
        cache_set(cache_key, result)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Failed to get county overview: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/voters/at')
def api_voters_at_location():
    """Look up voter(s) at a specific lat/lng for a given election.
    
    Used for lazy-loading popup details when a user clicks a marker.
    Matches voters within ~11m (0.0001 degree) of the given coordinates.
    
    Query params:
        lat, lng (required)
        election_date (required)
        voting_method (optional)
    """
    try:
        lat = request.args.get('lat', type=float)
        lng = request.args.get('lng', type=float)
        election_date = request.args.get('election_date')
        voting_method = request.args.get('voting_method')
        
        if lat is None or lng is None or not election_date:
            return jsonify({'error': 'lat, lng, and election_date are required'}), 400
        
        voters = db.get_voters_at_location(lat, lng, election_date, voting_method)
        return jsonify({'voters': voters, 'count': len(voters)})
    except Exception as e:
        logger.error(f"Failed to get voters at location: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/registered-voters')
def api_registered_voters():
    """Get geocoded registered voters who have NOT voted in the current election.

    Query params:
        county (required — comma-separated for multiple)
        election_date (required)
        sw_lat, sw_lng, ne_lat, ne_lng (required — viewport bounds)
        limit (optional)
    """
    try:
        county_param = request.args.get('county', 'Hidalgo')
        counties = [c.strip() for c in county_param.split(',') if c.strip()]
        election_date = request.args.get('election_date')
        limit = request.args.get('limit', type=int)

        if not election_date:
            return jsonify({'error': 'election_date is required'}), 400

        # Viewport bounds are required for this endpoint (100K+ voters)
        sw_lat = request.args.get('sw_lat', type=float)
        sw_lng = request.args.get('sw_lng', type=float)
        ne_lat = request.args.get('ne_lat', type=float)
        ne_lng = request.args.get('ne_lng', type=float)
        if not all(v is not None for v in [sw_lat, sw_lng, ne_lat, ne_lng]):
            return jsonify({'error': 'Viewport bounds (sw_lat, sw_lng, ne_lat, ne_lng) are required'}), 400

        bounds = {'sw_lat': sw_lat, 'sw_lng': sw_lng,
                  'ne_lat': ne_lat, 'ne_lng': ne_lng}

        all_voters = []
        for county in counties:
            voters = db.get_registered_not_voted(county, election_date, bounds, limit)
            all_voters.extend(voters)

        features = []
        for v in all_voters:
            features.append({
                'type': 'Feature',
                'geometry': {'type': 'Point', 'coordinates': [v['lng'], v['lat']]},
                'properties': {
                    'vuid': v['vuid'],
                    'name': f"{v['firstname'] or ''} {v['lastname'] or ''}".strip(),
                    'firstname': v['firstname'] or '',
                    'lastname': v['lastname'] or '',
                    'address': v['address'] or '',
                    'precinct': v['precinct'] or '',
                    'sex': v['sex'] or '',
                    'birth_year': v['birth_year'] or 0,
                    'county': v.get('county', ''),
                    'current_party': v.get('current_party', ''),
                    'registered_party': v.get('registered_party', ''),
                    'party_affiliation_current': v.get('current_party', ''),
                    'voted_in_current_election': False,
                    'is_registered': True,
                    'is_new_voter': False,
                    'has_switched_parties': False,
                    'party_affiliation_previous': '',
                },
            })

        response = jsonify({
            'type': 'FeatureCollection',
            'features': features,
        })
        response.headers['Cache-Control'] = 'public, max-age=120'
        return response
    except Exception as e:
        logger.error(f"Failed to get registered voters: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/search-voters')
def search_voters():
    """Search voters by any field: VUID, name, address, DOB, precinct, etc.
    Returns voter info + vote history + household members at same address.
    Requires authenticated session with approved/superadmin/admin role."""
    token = request.cookies.get('session_token')
    session = get_session_info(token)
    if not session or session.get('role') not in ('approved', 'superadmin', 'admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    q = (request.args.get('q') or '').strip()
    if not q or len(q) < 2:
        return jsonify({'error': 'Query must be at least 2 characters'}), 400

    try:
        conn = db.get_connection()
        rows = []
        limit = 30

        # Check if query looks like a VUID (numeric, 8+ digits)
        if q.isdigit() and len(q) >= 8:
            rows = conn.execute(
                "SELECT * FROM voters WHERE vuid = ? LIMIT 1", (q,)
            ).fetchall()

        # Check if query looks like a birth year (4 digits, 19xx or 20xx)
        if not rows and q.isdigit() and len(q) == 4 and (q.startswith('19') or q.startswith('20')):
            rows = conn.execute(
                "SELECT * FROM voters WHERE birth_year = ? AND geocoded = 1 ORDER BY lastname, firstname LIMIT ?",
                (int(q), limit)
            ).fetchall()

        # General search: name, address, VUID partial, precinct
        if not rows:
            like = f'%{q}%'
            upper_like = f'%{q.upper()}%'
            rows = conn.execute("""
                SELECT * FROM voters
                WHERE (lastname LIKE ? OR firstname LIKE ?
                       OR address LIKE ? OR vuid LIKE ?
                       OR city LIKE ? OR precinct LIKE ?
                       OR (firstname || ' ' || lastname) LIKE ?
                       OR (lastname || ' ' || firstname) LIKE ?)
                AND geocoded = 1
                ORDER BY lastname, firstname
                LIMIT ?
            """, (upper_like, upper_like, upper_like, like,
                  upper_like, like, upper_like, upper_like, limit)).fetchall()

        # Enrich each result with vote history and household members
        results = []
        for row in rows:
            v = dict(row)
            vuid = v.get('vuid', '')

            # Vote history
            history = []
            if vuid:
                ve_rows = conn.execute("""
                    SELECT election_date, election_type, voting_method, party_voted
                    FROM voter_elections WHERE vuid = ?
                    ORDER BY election_date
                """, (vuid,)).fetchall()
                for ve in ve_rows:
                    party = ve[3] or ''
                    pl = party.lower()
                    if 'democrat' in pl or pl == 'd' or pl == 'dem':
                        party = 'Democratic'
                    elif 'republican' in pl or pl == 'r' or pl == 'rep':
                        party = 'Republican'
                    if party:
                        history.append({
                            'date': ve[0] or '',
                            'type': ve[1] or '',
                            'method': ve[2] or '',
                            'party': party,
                        })
            v['history'] = history

            # Household members at same address
            household = []
            addr = (v.get('address') or '').strip().upper()
            if addr and vuid:
                hh_rows = conn.execute("""
                    SELECT vuid, firstname, middlename, lastname, suffix, sex,
                           birth_year, current_party
                    FROM voters WHERE address = ? AND vuid != ?
                    ORDER BY lastname, firstname
                    LIMIT 20
                """, (addr, vuid)).fetchall()
                for hh in hh_rows:
                    hh_vuid = hh[0]
                    hh_hist = []
                    hh_ve = conn.execute("""
                        SELECT election_date, election_type, voting_method, party_voted
                        FROM voter_elections WHERE vuid = ?
                        ORDER BY election_date
                    """, (hh_vuid,)).fetchall()
                    for ve in hh_ve:
                        party = ve[3] or ''
                        pl = party.lower()
                        if 'democrat' in pl or pl == 'd' or pl == 'dem':
                            party = 'Democratic'
                        elif 'republican' in pl or pl == 'r' or pl == 'rep':
                            party = 'Republican'
                        if party:
                            hh_hist.append({
                                'date': ve[0] or '',
                                'type': ve[1] or '',
                                'method': ve[2] or '',
                                'party': party,
                            })
                    household.append({
                        'vuid': hh_vuid,
                        'name': ' '.join(filter(None, [hh[1], hh[2], hh[3], hh[4]])),
                        'sex': hh[5] or '',
                        'birth_year': hh[6],
                        'current_party': hh[7] or '',
                        'history': hh_hist,
                    })
            v['household'] = household

            results.append(v)

        return jsonify({'results': results, 'total': len(results), 'query': q})

    except Exception as e:
        logger.error(f"Voter search failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/election-insights')
def election_insights():
    """Return computed election insights/stats for the newspaper overlay.
    
    Serves pre-computed data from cache file (updated after each scrape).
    Falls back to live computation if cache doesn't exist.
    """
    try:
        # Check for pre-computed cache file first (instant response)
        cache_file = Path('/opt/whovoted/public/cache/gazette_insights.json')
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return jsonify(json.load(f))
        
        # Fallback: compute live (slow)
        logger.warning("Gazette cache miss - computing live (slow)")
        conn = db.get_connection()

        # Overall turnout
        ev_2022 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND voting_method='early-voting'").fetchone()[0]
        ed_2022 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND voting_method='election-day'").fetchone()[0]
        ev_2024 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND voting_method='early-voting'").fetchone()[0]
        ed_2024 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND voting_method='election-day'").fetchone()[0]
        ev_2026 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03'").fetchone()[0]

        total_2022 = ev_2022 + ed_2022
        total_2024 = ev_2024 + ed_2024

        # Party breakdown
        dem_2022 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND party_voted='Democratic'").fetchone()[0]
        rep_2022 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2022-03-01' AND party_voted='Republican'").fetchone()[0]
        dem_2024 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND party_voted='Democratic'").fetchone()[0]
        rep_2024 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2024-03-05' AND party_voted='Republican'").fetchone()[0]
        dem_2026 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Democratic'").fetchone()[0]
        rep_2026 = conn.execute("SELECT COUNT(*) FROM voter_elections WHERE election_date='2026-03-03' AND party_voted='Republican'").fetchone()[0]

        # Flips
        def get_flips(edate):
            rows = conn.execute("""
                SELECT ve_current.party_voted as to_p, ve_prev.party_voted as from_p, COUNT(*) as cnt
                FROM voter_elections ve_current
                JOIN voter_elections ve_prev ON ve_current.vuid = ve_prev.vuid
                WHERE ve_current.election_date = ?
                    AND ve_prev.election_date = (
                        SELECT MAX(ve2.election_date) FROM voter_elections ve2
                        WHERE ve2.vuid = ve_current.vuid AND ve2.election_date < ve_current.election_date
                            AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
                    AND ve_current.party_voted != ve_prev.party_voted
                    AND ve_current.party_voted != '' AND ve_prev.party_voted != ''
                GROUP BY ve_current.party_voted, ve_prev.party_voted
            """, (edate,)).fetchall()
            r2d = sum(r[2] for r in rows if r[1] == 'Republican' and r[0] == 'Democratic')
            d2r = sum(r[2] for r in rows if r[1] == 'Democratic' and r[0] == 'Republican')
            return r2d, d2r

        r2d_2024, d2r_2024 = get_flips('2024-03-05')
        r2d_2026, d2r_2026 = get_flips('2026-03-03')

        # New voters — only count from counties that have prior election data
        # (otherwise statewide EVR data inflates the count with voters we simply
        # haven't seen before, not genuinely new voters)
        new_2026 = conn.execute("""
            SELECT COUNT(*) FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = '2026-03-03'
              AND EXISTS (SELECT 1 FROM voter_elections ve_prior
                  JOIN voters v2 ON ve_prior.vuid = v2.vuid
                  WHERE v2.county = v.county AND ve_prior.election_date < '2026-03-03'
                    AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
                  LIMIT 1)
              AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
                  WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
        """).fetchone()[0]
        new_dem_2026 = conn.execute("""
            SELECT COUNT(*) FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = '2026-03-03' AND ve.party_voted = 'Democratic'
              AND EXISTS (SELECT 1 FROM voter_elections ve_prior
                  JOIN voters v2 ON ve_prior.vuid = v2.vuid
                  WHERE v2.county = v.county AND ve_prior.election_date < '2026-03-03'
                    AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
                  LIMIT 1)
              AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
                  WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
        """).fetchone()[0]
        new_rep_2026 = conn.execute("""
            SELECT COUNT(*) FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = '2026-03-03' AND ve.party_voted = 'Republican'
              AND EXISTS (SELECT 1 FROM voter_elections ve_prior
                  JOIN voters v2 ON ve_prior.vuid = v2.vuid
                  WHERE v2.county = v.county AND ve_prior.election_date < '2026-03-03'
                    AND ve_prior.party_voted != '' AND ve_prior.party_voted IS NOT NULL
                  LIMIT 1)
              AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
                  WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
        """).fetchone()[0]

        # New voter age/gender breakdown for 2026
        new_age_rows = conn.execute("""
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
                v.sex,
                COUNT(*) as cnt
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = '2026-03-03'
              AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
                  WHERE ve2.vuid = ve.vuid AND ve2.election_date < '2026-03-03'
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
            GROUP BY age_group, v.sex
        """).fetchall()
        new_age_gender_2026 = {}
        for row in new_age_rows:
            ag, sex, cnt = row[0], row[1] or 'U', row[2]
            if ag not in new_age_gender_2026:
                new_age_gender_2026[ag] = {'total': 0, 'female': 0, 'male': 0}
            new_age_gender_2026[ag]['total'] += cnt
            if sex == 'F':
                new_age_gender_2026[ag]['female'] += cnt
            elif sex == 'M':
                new_age_gender_2026[ag]['male'] += cnt

        # Gender breakdown for 2026
        female_2026 = conn.execute("""
            SELECT COUNT(*) FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date='2026-03-03' AND v.sex='F'
        """).fetchone()[0]
        male_2026 = conn.execute("""
            SELECT COUNT(*) FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date='2026-03-03' AND v.sex='M'
        """).fetchone()[0]
        dem_female_2026 = conn.execute("""
            SELECT COUNT(*) FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date='2026-03-03' AND ve.party_voted='Democratic' AND v.sex='F'
        """).fetchone()[0]
        dem_male_2026 = conn.execute("""
            SELECT COUNT(*) FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date='2026-03-03' AND ve.party_voted='Democratic' AND v.sex='M'
        """).fetchone()[0]
        rep_female_2026 = conn.execute("""
            SELECT COUNT(*) FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date='2026-03-03' AND ve.party_voted='Republican' AND v.sex='F'
        """).fetchone()[0]
        rep_male_2026 = conn.execute("""
            SELECT COUNT(*) FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date='2026-03-03' AND ve.party_voted='Republican' AND v.sex='M'
        """).fetchone()[0]

        # Age group breakdown for 2026
        age_rows = conn.execute("""
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
            WHERE ve.election_date = '2026-03-03'
            GROUP BY age_group, ve.party_voted
        """).fetchall()
        age_groups_2026 = {}
        for row in age_rows:
            ag, party, cnt = row[0], row[1], row[2]
            if ag not in age_groups_2026:
                age_groups_2026[ag] = {'total': 0, 'dem': 0, 'rep': 0}
            age_groups_2026[ag]['total'] += cnt
            if party == 'Democratic':
                age_groups_2026[ag]['dem'] += cnt
            elif party == 'Republican':
                age_groups_2026[ag]['rep'] += cnt

        # Returning / lapsed
        both_24_26 = conn.execute("""
            SELECT COUNT(DISTINCT ve26.vuid) FROM voter_elections ve26
            JOIN voter_elections ve24 ON ve26.vuid = ve24.vuid
            WHERE ve26.election_date = '2026-03-03' AND ve24.election_date = '2024-03-05'
        """).fetchone()[0]
        voted_24_not_26 = conn.execute("""
            SELECT COUNT(DISTINCT ve24.vuid) FROM voter_elections ve24
            WHERE ve24.election_date = '2024-03-05'
              AND NOT EXISTS (SELECT 1 FROM voter_elections ve26
                  WHERE ve26.vuid = ve24.vuid AND ve26.election_date = '2026-03-03')
        """).fetchone()[0]

        dem_share_2022 = round(dem_2022 / (dem_2022 + rep_2022) * 100, 1) if (dem_2022 + rep_2022) else 0
        dem_share_2024 = round(dem_2024 / (dem_2024 + rep_2024) * 100, 1) if (dem_2024 + rep_2024) else 0
        dem_share_2026 = round(dem_2026 / (dem_2026 + rep_2026) * 100, 1) if (dem_2026 + rep_2026) else 0
        pct_of_2024 = round(ev_2026 / total_2024 * 100, 1) if total_2024 else 0

        # Last updated: most recent created_at from voter_elections for 2026
        last_row = conn.execute("""
            SELECT MAX(ve.created_at) FROM voter_elections ve
            WHERE ve.election_date = '2026-03-03'
        """).fetchone()
        last_updated = last_row[0] if last_row and last_row[0] else None

        from datetime import datetime, timezone
        generated_at = datetime.now(timezone.utc).isoformat()

        return jsonify({
            'ev_2022': ev_2022, 'ed_2022': ed_2022, 'total_2022': total_2022,
            'ev_2024': ev_2024, 'ed_2024': ed_2024, 'total_2024': total_2024,
            'ev_2026': ev_2026,
            'dem_2026': dem_2026, 'rep_2026': rep_2026,
            'dem_share_2022': dem_share_2022, 'dem_share_2024': dem_share_2024, 'dem_share_2026': dem_share_2026,
            'pct_of_2024': pct_of_2024,
            'r2d_2024': r2d_2024, 'd2r_2024': d2r_2024,
            'r2d_2026': r2d_2026, 'd2r_2026': d2r_2026,
            'new_2026': new_2026, 'new_dem_2026': new_dem_2026, 'new_rep_2026': new_rep_2026,
            'both_24_26': both_24_26, 'voted_24_not_26': voted_24_not_26,
            'female_2026': female_2026, 'male_2026': male_2026,
            'dem_female_2026': dem_female_2026, 'dem_male_2026': dem_male_2026,
            'rep_female_2026': rep_female_2026, 'rep_male_2026': rep_male_2026,
            'age_groups_2026': age_groups_2026,
            'new_age_gender_2026': new_age_gender_2026,
            'last_updated': last_updated,
            'generated_at': generated_at,
        })
    except Exception as e:
        logger.error(f"Election insights failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/county-report')
def county_report():
    """Return county-specific election insights for mini-gazette.
    
    Query params:
        county (required): County name
        election_date (required): Election date (YYYY-MM-DD)
        voting_method (optional): Filter by voting method
    
    Serves pre-computed data from cache file when available.
    """
    try:
        county = request.args.get('county', '').strip()
        election_date = request.args.get('election_date', '').strip()
        voting_method = request.args.get('voting_method', '').strip()
        
        if not county or not election_date:
            return jsonify({'error': 'county and election_date are required'}), 400
        
        # Check for pre-computed cache file first
        method_str = voting_method or 'all'
        cache_file = Path(f'/opt/whovoted/public/cache/county_report_{county}_{election_date}_{method_str}.json')
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                return jsonify(json.load(f))
        
        # Fallback: compute live (slower)
        logger.warning(f"County report cache miss for {county}/{election_date} - computing live")
        conn = db.get_connection()
        
        # Build WHERE clause for county + election_date + optional voting_method
        where_base = "WHERE v.county = ? AND ve.election_date = ?"
        params_base = [county, election_date]
        if voting_method:
            where_base += " AND ve.voting_method = ?"
            params_base.append(voting_method)
        
        # Total voters for this county/election
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
        
        # New voters (county-specific, only if county has prior data)
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
        
        # Party switchers (flips)
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
        
        # Gender breakdown
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
        
        # Last updated
        last_row = conn.execute(f"""
            SELECT MAX(ve.created_at) FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            {where_base}
        """, params_base).fetchone()
        last_updated = last_row[0] if last_row and last_row[0] else None
        
        from datetime import datetime, timezone
        generated_at = datetime.now(timezone.utc).isoformat()
        
        result = {
            'county': county,
            'election_date': election_date,
            'voting_method': voting_method or 'all',
            'total_voters': total_voters,
            'dem_count': dem_count,
            'rep_count': rep_count,
            'dem_share': dem_share,
            'new_voters': new_voters,
            'new_dem': new_dem,
            'new_rep': new_rep,
            'new_dem_pct': new_dem_pct,
            'r2d': r2d,
            'd2r': d2r,
            'female_count': female_count,
            'male_count': male_count,
            'female_pct': female_pct,
            'age_groups': age_groups,
            'last_updated': last_updated,
            'generated_at': generated_at,
        }
        
        conn.close()
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"County report failed: {e}")
        return jsonify({'error': str(e)}), 500


def _lookup_vuids_by_coords(conn, coords, election_date):
    """Look up VUIDs from a list of [lng, lat] coordinate pairs.
    
    Uses a small tolerance to match voters near each coordinate.
    Batches the lookup for efficiency.
    """
    if not coords:
        return []
    
    tolerance = 0.0001  # ~11 meters
    vuid_set = set()
    
    # Build a single query with OR conditions for all coords (batched)
    for i in range(0, len(coords), 200):
        batch = coords[i:i+200]
        conditions = []
        params = []
        for c in batch:
            lng, lat = c[0], c[1]
            conditions.append("(v.lat BETWEEN ? AND ? AND v.lng BETWEEN ? AND ?)")
            params.extend([lat - tolerance, lat + tolerance, lng - tolerance, lng + tolerance])
        
        where = " OR ".join(conditions)
        rows = conn.execute(f"""
            SELECT DISTINCT ve.vuid FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            WHERE ve.election_date = ? AND ({where})
              AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
        """, [election_date] + params).fetchall()
        
        for r in rows:
            vuid_set.add(r[0])
    
    return list(vuid_set)


def _point_in_polygon(lng, lat, polygon):
    """Ray-casting point-in-polygon test. polygon is list of [lng, lat]."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def _point_in_feature(lng, lat, geometry):
    """Check if point is inside a GeoJSON geometry (Polygon or MultiPolygon)."""
    gtype = geometry.get('type', '')
    coords = geometry.get('coordinates', [])
    if gtype == 'Polygon':
        return _point_in_polygon(lng, lat, coords[0])
    elif gtype == 'MultiPolygon':
        return any(_point_in_polygon(lng, lat, poly[0]) for poly in coords)
    return False


def _lookup_vuids_by_polygon(conn, geometry, election_date):
    """Find all VUIDs for voters whose geocoded location falls inside a polygon.
    
    Uses bounding-box pre-filter in SQL, then Python point-in-polygon refinement.
    Works across ALL counties — not limited to the currently loaded map data.
    """
    coords = geometry.get('coordinates', [])
    gtype = geometry.get('type', '')
    
    # Compute bounding box of the polygon
    all_points = []
    if gtype == 'Polygon':
        all_points = coords[0]
    elif gtype == 'MultiPolygon':
        for poly in coords:
            all_points.extend(poly[0])
    
    if not all_points:
        return []
    
    min_lng = min(p[0] for p in all_points)
    max_lng = max(p[0] for p in all_points)
    min_lat = min(p[1] for p in all_points)
    max_lat = max(p[1] for p in all_points)
    
    # Bounding-box pre-filter from DB
    rows = conn.execute("""
        SELECT DISTINCT ve.vuid, v.lng, v.lat FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = ?
          AND v.lat BETWEEN ? AND ?
          AND v.lng BETWEEN ? AND ?
          AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
          AND v.lat IS NOT NULL AND v.lng IS NOT NULL
    """, [election_date, min_lat, max_lat, min_lng, max_lng]).fetchall()
    
    # Refine with point-in-polygon
    vuids = []
    for r in rows:
        if _point_in_feature(r['lng'], r['lat'], geometry):
            vuids.append(r['vuid'])
    
    logger.info(f"Polygon lookup: bbox returned {len(rows)} candidates, {len(vuids)} inside polygon")
    return vuids


def district_stats():
    """Return turnout stats for voters within a specific district boundary.

    Accepts:
    - POST with JSON body {"vuids": [...]} for direct VUID list
    - POST with JSON body {"coords": [[lng,lat], ...]} for coordinate-based lookup
    - POST with JSON body {"polygon": {GeoJSON geometry}} for full district boundary
    - GET with ?vuids=comma,separated,list for small sets

    Optimized: uses temp table + single-pass queries instead of chunked IN clauses.
    Serves pre-computed cache when available (updated after each scrape).
    """
    try:
        # Check for pre-computed cache file first (instant response)
        district_id = request.args.get('district_id', '')
        district_name = request.args.get('district_name', '')
        if request.method == 'POST':
            data = request.get_json() or {}
            if not district_id:
                district_id = data.get('district_id', '')
            if not district_name:
                district_name = data.get('district_name', '')
        
        # Use district_name for cache lookup (matches how cache files are generated)
        if district_name:
            safe_name = district_name.replace(' ', '_').replace('/', '_')
            cache_file = Path(f'/opt/whovoted/public/cache/district_report_{safe_name}.json')
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    cached_data = json.load(f)
                    # Verify cache has all required fields (some old caches are incomplete)
                    required_fields = ['age_groups', 'new_age_gender', 'female', 'male', 'total_2024']
                    if all(field in cached_data for field in required_fields):
                        logger.info(f"District stats cache HIT for {district_name}")
                        # Add success flag for API compatibility
                        cached_data['success'] = True
                        return jsonify(cached_data)
                    else:
                        logger.warning(f"District stats cache INCOMPLETE for {district_name} - missing fields, computing live")
        
        # Fallback: compute live (slower)
        logger.warning(f"District stats cache miss for {district_id} - computing live")
        
        conn = db.get_connection()

        # Get VUIDs from request
        if request.method == 'POST':
            data = request.get_json() or {}
            vuids = data.get('vuids', [])
            coords = data.get('coords', [])
            polygon = data.get('polygon')
            election_date = data.get('election_date', request.args.get('election_date', '2026-03-03'))

            if not vuids and polygon:
                vuids = _lookup_vuids_by_polygon(conn, polygon, election_date)
            elif not vuids and coords:
                vuids = _lookup_vuids_by_coords(conn, coords, election_date)
        else:
            vuids_param = request.args.get('vuids', '')
            vuids = [v.strip() for v in vuids_param.split(',') if v.strip()] if vuids_param else []
            election_date = request.args.get('election_date', '2026-03-03')

        if not vuids:
            return jsonify({'error': 'No VUIDs provided'}), 400

        # Load VUIDs into a temp table for efficient bulk queries
        conn.execute("CREATE TEMP TABLE IF NOT EXISTS _ds_vuids(vuid TEXT PRIMARY KEY)")
        conn.execute("DELETE FROM _ds_vuids")
        for i in range(0, len(vuids), 5000):
            chunk = vuids[i:i+5000]
            conn.executemany("INSERT OR IGNORE INTO _ds_vuids(vuid) VALUES(?)", [(v,) for v in chunk])

        # Core stats: total, party, gender — single query
        core = conn.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem,
                SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as rep,
                SUM(CASE WHEN v.sex = 'F' THEN 1 ELSE 0 END) as female,
                SUM(CASE WHEN v.sex = 'M' THEN 1 ELSE 0 END) as male,
                SUM(CASE WHEN ve.party_voted = 'Democratic' AND v.sex = 'F' THEN 1 ELSE 0 END) as dem_female,
                SUM(CASE WHEN ve.party_voted = 'Democratic' AND v.sex = 'M' THEN 1 ELSE 0 END) as dem_male,
                SUM(CASE WHEN ve.party_voted = 'Republican' AND v.sex = 'F' THEN 1 ELSE 0 END) as rep_female,
                SUM(CASE WHEN ve.party_voted = 'Republican' AND v.sex = 'M' THEN 1 ELSE 0 END) as rep_male
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            INNER JOIN _ds_vuids t ON ve.vuid = t.vuid
            WHERE ve.election_date = ?
        """, [election_date]).fetchone()

        total = core['total'] or 0
        dem = core['dem'] or 0
        rep = core['rep'] or 0
        female = core['female'] or 0
        male = core['male'] or 0
        dem_female = core['dem_female'] or 0
        dem_male = core['dem_male'] or 0
        rep_female = core['rep_female'] or 0
        rep_male = core['rep_male'] or 0

        # Flips — single query
        flip_rows = conn.execute("""
            SELECT ve_cur.party_voted as to_p, ve_prev.party_voted as from_p, COUNT(*) as cnt
            FROM voter_elections ve_cur
            INNER JOIN _ds_vuids t ON ve_cur.vuid = t.vuid
            INNER JOIN voter_elections ve_prev ON ve_cur.vuid = ve_prev.vuid
            WHERE ve_cur.election_date = ?
              AND ve_prev.election_date = (
                  SELECT MAX(ve2.election_date) FROM voter_elections ve2
                  WHERE ve2.vuid = ve_cur.vuid AND ve2.election_date < ?
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
              AND ve_cur.party_voted != ve_prev.party_voted
              AND ve_cur.party_voted != '' AND ve_prev.party_voted != ''
            GROUP BY ve_cur.party_voted, ve_prev.party_voted
        """, [election_date, election_date]).fetchall()
        r2d = sum(r['cnt'] for r in flip_rows if r['from_p'] == 'Republican' and r['to_p'] == 'Democratic')
        d2r = sum(r['cnt'] for r in flip_rows if r['from_p'] == 'Democratic' and r['to_p'] == 'Republican')

        # New voters — single query
        new_row = conn.execute("""
            SELECT
                COUNT(*) as new_total,
                SUM(CASE WHEN ve.party_voted = 'Democratic' THEN 1 ELSE 0 END) as new_dem,
                SUM(CASE WHEN ve.party_voted = 'Republican' THEN 1 ELSE 0 END) as new_rep
            FROM voter_elections ve
            INNER JOIN _ds_vuids t ON ve.vuid = t.vuid
            WHERE ve.election_date = ?
              AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
                  WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
        """, [election_date, election_date]).fetchone()
        new_total = new_row['new_total'] or 0
        new_dem = new_row['new_dem'] or 0
        new_rep = new_row['new_rep'] or 0

        # New voter age/gender breakdown — single query
        new_age_gender = {}
        nag_rows = conn.execute("""
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
                v.sex, COUNT(*) as cnt
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            INNER JOIN _ds_vuids t ON ve.vuid = t.vuid
            WHERE ve.election_date = ?
              AND NOT EXISTS (SELECT 1 FROM voter_elections ve2
                  WHERE ve2.vuid = ve.vuid AND ve2.election_date < ?
                    AND ve2.party_voted != '' AND ve2.party_voted IS NOT NULL)
            GROUP BY age_group, v.sex
        """, [election_date, election_date]).fetchall()
        for row in nag_rows:
            ag, sex, cnt = row['age_group'], row['sex'] or 'U', row['cnt']
            if ag not in new_age_gender:
                new_age_gender[ag] = {'total': 0, 'female': 0, 'male': 0}
            new_age_gender[ag]['total'] += cnt
            if sex == 'F': new_age_gender[ag]['female'] += cnt
            elif sex == 'M': new_age_gender[ag]['male'] += cnt

        # Age group breakdown — single query
        age_groups = {}
        ag_rows = conn.execute("""
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
                ve.party_voted, COUNT(*) as cnt
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            INNER JOIN _ds_vuids t ON ve.vuid = t.vuid
            WHERE ve.election_date = ?
            GROUP BY age_group, ve.party_voted
        """, [election_date]).fetchall()
        for row in ag_rows:
            ag, party, cnt = row['age_group'], row['party_voted'], row['cnt']
            if ag not in age_groups:
                age_groups[ag] = {'total': 0, 'dem': 0, 'rep': 0}
            age_groups[ag]['total'] += cnt
            if party == 'Democratic': age_groups[ag]['dem'] += cnt
            elif party == 'Republican': age_groups[ag]['rep'] += cnt

        # 2024 comparison — single query
        comp = conn.execute("""
            SELECT
                COUNT(*) as total_2024,
                SUM(CASE WHEN party_voted = 'Democratic' THEN 1 ELSE 0 END) as dem_2024,
                SUM(CASE WHEN party_voted = 'Republican' THEN 1 ELSE 0 END) as rep_2024
            FROM voter_elections ve
            INNER JOIN _ds_vuids t ON ve.vuid = t.vuid
            WHERE ve.election_date = '2024-03-05'
        """).fetchone()
        total_2024 = comp['total_2024'] or 0
        dem_2024 = comp['dem_2024'] or 0
        rep_2024 = comp['rep_2024'] or 0

        # County breakdown — single query
        county_breakdown = {}
        cb_rows = conn.execute("""
            SELECT v.county, ve.party_voted, COUNT(*) as cnt
            FROM voter_elections ve
            JOIN voters v ON ve.vuid = v.vuid
            INNER JOIN _ds_vuids t ON ve.vuid = t.vuid
            WHERE ve.election_date = ?
              AND ve.party_voted != '' AND ve.party_voted IS NOT NULL
            GROUP BY v.county, ve.party_voted
        """, [election_date]).fetchall()
        for row in cb_rows:
            county = row['county'] or 'Unknown'
            party, cnt = row['party_voted'], row['cnt']
            if county not in county_breakdown:
                county_breakdown[county] = {'total': 0, 'dem': 0, 'rep': 0}
            county_breakdown[county]['total'] += cnt
            if party == 'Democratic': county_breakdown[county]['dem'] += cnt
            elif party == 'Republican': county_breakdown[county]['rep'] += cnt

        conn.execute("DROP TABLE IF EXISTS _ds_vuids")

        dem_share = round(dem / (dem + rep) * 100, 1) if (dem + rep) else 0
        dem_share_2024 = round(dem_2024 / (dem_2024 + rep_2024) * 100, 1) if (dem_2024 + rep_2024) else 0

        return jsonify({
            'district_id': district_id,
            'election_date': election_date,
            'total': total,
            'dem': dem,
            'rep': rep,
            'dem_share': dem_share,
            'new_total': new_total,
            'new_dem': new_dem,
            'new_rep': new_rep,
            'r2d': r2d,
            'd2r': d2r,
            'total_2024': total_2024,
            'dem_2024': dem_2024,
            'rep_2024': rep_2024,
            'dem_share_2024': dem_share_2024,
            'female': female,
            'male': male,
            'dem_female': dem_female,
            'dem_male': dem_male,
            'rep_female': rep_female,
            'rep_male': rep_male,
            'age_groups': age_groups,
            'new_age_gender': new_age_gender,
            'county_breakdown': county_breakdown,
        })
    except Exception as e:
        logger.error(f"District stats failed: {e}")
        return jsonify({'error': str(e)}), 500


# Make district-stats accept both GET and POST
app.add_url_rule('/api/district-stats', 'district_stats_post', district_stats, methods=['POST'])

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login — legacy password login removed.
    GET redirects to main page (use Google SSO via account icon).
    POST returns 410 Gone."""
    if request.method == 'GET':
        return redirect('/')
    return jsonify({'success': False, 'error': 'Legacy login removed. Use Google Sign-In.'}), 410

@app.route('/admin/logout', methods=['POST'])
def admin_logout():
    """Admin logout."""
    token = request.cookies.get('session_token')
    if token:
        invalidate_session(token)
    
    response = jsonify({'success': True})
    response.set_cookie('session_token', '', expires=0)
    return response

@app.route('/admin')
@require_auth
def admin_dashboard():
    """Admin dashboard page."""
    admin_dir = Path(__file__).parent / 'admin'
    return send_from_directory(admin_dir, 'dashboard.html')

@app.route('/admin/dashboard.js')
def admin_dashboard_js():
    """Serve admin dashboard JavaScript with no-cache headers."""
    admin_dir = Path(__file__).parent / 'admin'
    response = send_from_directory(admin_dir, 'dashboard.js', mimetype='application/javascript')
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


# ============================================================================
# GOOGLE SSO & USER MANAGEMENT
# ============================================================================

@app.route('/auth/google', methods=['POST'])
def google_auth():
    """Handle Google Sign-In. Verify token, create/get user, create session."""
    data = request.get_json()
    id_token = data.get('credential') or data.get('id_token')
    if not id_token:
        return jsonify({'error': 'No credential provided'}), 400

    google_info = verify_google_token(id_token)
    if not google_info:
        return jsonify({'error': 'Invalid Google token'}), 401

    user = get_or_create_user(google_info)
    role = user.get('role', 'pending')

    # Create session with role info
    token = create_session(user['email'], role=role, email=user['email'])

    response = jsonify({
        'success': True,
        'user': {
            'email': user['email'],
            'name': user.get('name', ''),
            'picture': user.get('picture', ''),
            'role': role,
        }
    })
    response.set_cookie('session_token', token, httponly=True,
                        secure=False, samesite='Lax',
                        max_age=Config.SESSION_TIMEOUT_HOURS * 3600)
    return response


@app.route('/auth/me', methods=['GET'])
def auth_me():
    """Get current user info from session."""
    token = request.cookies.get('session_token')
    session = get_session_info(token)
    if not session:
        return jsonify({'authenticated': False, 'role': 'visitor'})

    return jsonify({
        'authenticated': True,
        'role': session.get('role', 'visitor'),
        'email': session.get('email', ''),
        'user_id': session.get('user_id', ''),
    })


@app.route('/auth/request-access', methods=['POST'])
def request_access():
    """Handle email-based access request (no Google SSO)."""
    data = request.get_json()
    email = (data.get('email') or '').strip().lower()
    if not email or '@' not in email:
        return jsonify({'error': 'Valid email is required'}), 400

    try:
        with db.get_db() as conn:
            existing = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            if existing:
                role = existing['role']
                if role == 'approved' or role == 'superadmin':
                    return jsonify({'success': True, 'message': 'This email already has access. Please sign in with Google.'})
                elif role == 'pending':
                    return jsonify({'success': True, 'message': 'Your request is already pending admin approval.'})
            else:
                conn.execute("""
                    INSERT INTO users (email, name, role, last_login)
                    VALUES (?, ?, 'pending', ?)
                """, (email, email.split('@')[0], datetime.now().isoformat()))
                logger.info(f"Email access request from: {email}")

        return jsonify({'success': True, 'message': 'Request submitted! An admin will review and approve your access.'})
    except Exception as e:
        logger.error(f"Access request failed: {e}")
        return jsonify({'error': 'Request failed. Please try again.'}), 500


@app.route('/auth/logout', methods=['POST'])
def auth_logout():
    """Logout current user."""
    token = request.cookies.get('session_token')
    if token:
        invalidate_session(token)
    response = jsonify({'success': True})
    response.set_cookie('session_token', '', expires=0)
    return response


@app.route('/admin/api/users', methods=['GET'])
@require_auth
def api_list_users():
    """List all users (admin only)."""
    token = request.cookies.get('session_token')
    session = get_session_info(token)
    if not session or session.get('role') not in ('superadmin', 'admin'):
        return jsonify({'error': 'Forbidden'}), 403
    users = list_users()
    return jsonify({'users': users})


@app.route('/admin/api/users/<int:user_id>', methods=['PUT'])
@require_auth
def api_update_user(user_id):
    """Update user role or info."""
    token = request.cookies.get('session_token')
    session = get_session_info(token)
    if not session or session.get('role') not in ('superadmin', 'admin'):
        return jsonify({'error': 'Forbidden'}), 403

    data = request.get_json()
    if 'role' in data:
        update_user_role(user_id, data['role'], approved_by=session.get('email', ''))
    if 'name' in data:
        update_user_info(user_id, name=data['name'])
    return jsonify({'success': True})


@app.route('/admin/api/users/<int:user_id>', methods=['DELETE'])
@require_auth
def api_delete_user(user_id):
    """Delete a user."""
    token = request.cookies.get('session_token')
    session = get_session_info(token)
    if not session or session.get('role') not in ('superadmin', 'admin'):
        return jsonify({'error': 'Forbidden'}), 403
    delete_user(user_id)
    return jsonify({'success': True})


@app.route('/admin/preview-columns', methods=['POST'])
@require_auth
def preview_columns():
    """Preview column mapping for an uploaded file. Reads first few rows and returns
    auto-mapped columns, unmapped columns, and saved county mappings."""
    try:
        from vuid_resolver import preview_column_mapping
        from processor import read_data_file

        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400

        file = request.files['file']
        county = request.form.get('county', '')

        # Save temporarily
        import tempfile, os
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name

        try:
            df = read_data_file(tmp_path)
            columns = list(df.columns)
            sample_rows = df.head(5).fillna('').astype(str).values.tolist()

            # Get saved mappings for this county
            saved_mappings = db.get_column_mappings(county) if county else {}

            # Preview the mapping
            result = preview_column_mapping(columns, custom_mappings=saved_mappings)
            result['columns'] = columns
            result['sample_rows'] = sample_rows
            result['saved_mappings'] = saved_mappings
            result['filename'] = file.filename

            return jsonify(result)
        finally:
            os.unlink(tmp_path)

    except Exception as e:
        logger.error(f"Column preview failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/save-column-mapping', methods=['POST'])
@require_auth
def save_column_mapping():
    """Save column mappings for a county."""
    try:
        data = request.json
        county = data.get('county', '')
        mappings = data.get('mappings', {})

        if not county:
            return jsonify({'error': 'County is required'}), 400
        if not mappings:
            return jsonify({'error': 'No mappings provided'}), 400

        db.save_column_mappings(county, mappings)
        return jsonify({'success': True, 'county': county, 'saved': len(mappings)})

    except Exception as e:
        logger.error(f"Save column mapping failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/get-column-mapping', methods=['GET'])
@require_auth
def get_column_mapping():
    """Get saved column mappings for a county."""
    try:
        county = request.args.get('county', '')
        if not county:
            return jsonify({'error': 'County is required'}), 400

        mappings = db.get_column_mappings(county)
        return jsonify({'success': True, 'county': county, 'mappings': mappings})

    except Exception as e:
        logger.error(f"Get column mapping failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/check-duplicates', methods=['POST'])
@require_auth
def check_duplicates():
    """Check if uploaded files would create duplicate datasets."""
    try:
        import json
        
        # Get file metadata from request
        files_metadata = request.json.get('files', [])
        
        if not files_metadata:
            return jsonify({'error': 'No file metadata provided'}), 400
        
        duplicates = []
        public_data_dir = Config.PUBLIC_DIR / 'data'
        
        # Check each file against existing datasets
        for file_meta in files_metadata:
            county = file_meta.get('county')
            year = file_meta.get('year')
            election_type = file_meta.get('election_type')
            election_date = file_meta.get('election_date')
            voting_method = file_meta.get('voting_method', 'early-voting')
            filename = file_meta.get('filename')
            
            # Look for existing metadata file with same characteristics
            if public_data_dir.exists():
                for metadata_file in public_data_dir.glob('metadata*.json'):
                    try:
                        with open(metadata_file, 'r') as f:
                            existing = json.load(f)
                        
                        # Check if this matches the uploaded file's characteristics
                        if (existing.get('county') == county and
                            existing.get('year') == year and
                            existing.get('election_type') == election_type and
                            existing.get('election_date') == election_date and
                            existing.get('voting_method') == voting_method):
                            
                            duplicates.append({
                                'filename': filename,
                                'county': county,
                                'year': year,
                                'election_type': election_type,
                                'election_date': election_date,
                                'voting_method': voting_method,
                                'existing_filename': existing.get('original_filename', 'Unknown'),
                                'existing_metadata_file': metadata_file.name,
                                'last_updated': existing.get('last_updated'),
                                'total_records': existing.get('total_addresses', 0)
                            })
                            break
                    except Exception as e:
                        logger.warning(f"Could not read metadata file {metadata_file.name}: {e}")
                        continue
        
        return jsonify({
            'success': True,
            'duplicates': duplicates,
            'has_duplicates': len(duplicates) > 0
        })
        
    except Exception as e:
        logger.error(f"Failed to check duplicates: {e}")
        return jsonify({'error': f'Failed to check duplicates: {str(e)}'}), 500

@app.route('/admin/analyze-url', methods=['POST'])
@require_auth
def analyze_url():
    """Analyze a URL to guess election metadata from filename/URL patterns."""
    import requests as req_lib
    from urllib.parse import urlparse, unquote
    
    data = request.get_json()
    url = (data or {}).get('url', '').strip()
    if not url:
        return jsonify({'error': 'No URL provided'}), 400
    
    try:
        # Do a HEAD request first to get filename from headers
        head_resp = req_lib.head(url, timeout=15, allow_redirects=True)
        
        # Get filename from Content-Disposition or URL path
        filename = ''
        cd = head_resp.headers.get('Content-Disposition', '')
        if 'filename=' in cd:
            filename = cd.split('filename=')[-1].strip('"\'')
        if not filename:
            path = urlparse(url).path
            filename = unquote(path.split('/')[-1]) if path else ''
        
        # Get file size
        content_length = head_resp.headers.get('Content-Length')
        size_bytes = int(content_length) if content_length else None
        content_type = head_resp.headers.get('Content-Type', '')
        
        # Determine file extension validity
        lower_fn = filename.lower()
        valid_ext = any(lower_fn.endswith(ext) for ext in ['.csv', '.xls', '.xlsx', '.pdf'])
        if not valid_ext:
            if 'csv' in content_type or 'text/plain' in content_type:
                filename = (filename or 'download') + '.csv'
            elif 'excel' in content_type or 'spreadsheet' in content_type:
                filename = (filename or 'download') + '.xlsx'
            elif 'pdf' in content_type:
                filename = (filename or 'download') + '.pdf'
        
        # Parse metadata from filename + URL
        fn_lower = filename.lower()
        url_lower = url.lower()
        combined = fn_lower + ' ' + url_lower
        
        # Guess county from URL/filename
        county = ''
        county_keywords = {
            'hidalgo': 'Hidalgo', 'cameron': 'Cameron', 'starr': 'Starr',
            'willacy': 'Willacy', 'brooks': 'Brooks', 'webb': 'Webb',
            'nueces': 'Nueces', 'bexar': 'Bexar', 'harris': 'Harris',
            'dallas': 'Dallas', 'tarrant': 'Tarrant', 'travis': 'Travis',
        }
        for kw, name in county_keywords.items():
            if kw in combined:
                county = name
                break
        
        # Guess voting method
        voting_method = ''
        if any(x in combined for x in ['abbm', 'mail-in', 'mail_in', 'mailin', 'mail ballot', 'absentee']):
            voting_method = 'mail-in'
        elif any(x in combined for x in ['early vot', 'early_vot', 'earlyvot', ' ev ', '_ev_', '-ev-', 'ev roster', 'ev_roster']):
            voting_method = 'early-voting'
        elif any(x in combined for x in ['election day', 'election_day', 'electionday', ' ed ', '_ed_', '-ed-', 'eday']):
            voting_method = 'election-day'
        
        # Guess election type and party
        election_type = ''
        if any(x in combined for x in ['primary', 'prim']):
            election_type = 'primary'
        elif 'general' in combined or 'gen_' in combined:
            election_type = 'general'
        elif 'runoff' in combined:
            election_type = 'runoff'
        elif 'special' in combined:
            election_type = 'special'
        
        # Detect party from filename
        party_hint = ''
        if any(x in combined for x in [' dem ', '_dem_', '-dem-', 'dem roster', 'dem_roster', 'democratic']):
            party_hint = 'democratic'
            if election_type == 'primary':
                election_type = 'primary-democratic'
        elif any(x in combined for x in [' rep ', '_rep_', '-rep-', 'rep roster', 'rep_roster', 'republican']):
            party_hint = 'republican'
            if election_type == 'primary':
                election_type = 'primary-republican'
        
        # Guess year
        import re
        year = ''
        year_match = re.search(r'20[12]\d', filename)
        if year_match:
            year = year_match.group()
        else:
            year_match = re.search(r'20[12]\d', url)
            if year_match:
                year = year_match.group()
        
        # Guess election date from filename patterns
        election_date = ''
        # First try human-readable date patterns like "March 3, 2026" or "March 3 2026"
        month_names = {
            'january': '01', 'february': '02', 'march': '03', 'april': '04',
            'may': '05', 'june': '06', 'july': '07', 'august': '08',
            'september': '09', 'october': '10', 'november': '11', 'december': '12',
        }
        for mname, mnum in month_names.items():
            m = re.search(mname + r'\s+(\d{1,2})\s*,?\s*(20\d{2})', combined)
            if m:
                day = int(m.group(1))
                yr = m.group(2)
                election_date = f"{yr}-{mnum}-{day:02d}"
                if not year:
                    year = yr
                break
        
        # Then try ISO-style dates
        if not election_date:
            date_patterns = [
                (r'(\d{4})-(\d{2})-(\d{2})', lambda m: f"{m.group(1)}-{m.group(2)}-{m.group(3)}"),
            ]
            for pat, fmt in date_patterns:
                m = re.search(pat, filename)
                if m:
                    d = fmt(m)
                    if d:
                        election_date = d
                        break
        
        # If no date found but we have a year, use known election dates
        if not election_date and year:
            known_dates = {
                '2016': '2016-03-01', '2018': '2018-03-06', '2020': '2020-03-03',
                '2022': '2022-03-01', '2024': '2024-03-05', '2026': '2026-03-03',
            }
            if year in known_dates and ('primary' in (election_type or '') or not election_type):
                election_date = known_dates[year]
        
        # Extract file timestamp from filename suffix pattern: _YYYYMMDDHHmmss (before extension)
        # e.g. "EV DEM Roster March 3, 2026 (Cumulative)_20260227070116.xlsx"
        file_timestamp = ''
        file_timestamp_display = ''
        ts_match = re.search(r'_(\d{14,18})\.\w+$', filename)
        if not ts_match:
            # Also try URL-encoded filenames
            ts_match = re.search(r'_(\d{14,18})\.\w+$', unquote(url))
        if ts_match:
            ts_digits = ts_match.group(1)
            try:
                ts_year = int(ts_digits[0:4])
                ts_month = int(ts_digits[4:6])
                ts_day = int(ts_digits[6:8])
                ts_hour = int(ts_digits[8:10])
                ts_min = int(ts_digits[10:12])
                ts_sec = int(ts_digits[12:14])
                if 2020 <= ts_year <= 2030 and 1 <= ts_month <= 12 and 1 <= ts_day <= 31:
                    from datetime import datetime as dt
                    ts_dt = dt(ts_year, ts_month, ts_day, ts_hour, ts_min, ts_sec)
                    file_timestamp = ts_dt.isoformat()
                    file_timestamp_display = ts_dt.strftime('%b %d, %Y at %I:%M:%S %p')
            except (ValueError, IndexError):
                pass
        
        # Detect if cumulative vs daily
        is_cumulative = 'cumulative' in combined
        
        return jsonify({
            'success': True,
            'filename': filename,
            'size_bytes': size_bytes,
            'content_type': content_type,
            'file_timestamp': file_timestamp,
            'file_timestamp_display': file_timestamp_display,
            'is_cumulative': is_cumulative,
            'guessed': {
                'county': county,
                'year': year or '2026',
                'election_type': election_type,
                'election_date': election_date,
                'voting_method': voting_method,
                'party_hint': party_hint,
            }
        })
    except req_lib.exceptions.RequestException as e:
        return jsonify({'error': f'Failed to reach URL: {str(e)}'}), 400
    except Exception as e:
        logger.error(f"Analyze URL failed: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/admin/fetch-url', methods=['POST'])
@require_auth
def fetch_url():
    """Download files from URLs and process them like regular uploads."""
    import requests as req_lib
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    urls = data.get('urls', [])
    if not urls or not any(u.strip() for u in urls):
        return jsonify({'error': 'No URLs provided'}), 400
    
    # Limit to 10 URLs
    urls = [u.strip() for u in urls if u.strip()][:10]
    
    county = data.get('county', '')
    year = data.get('year', '')
    election_type = data.get('election_type', '')
    election_date = data.get('election_date', '')
    voting_method = data.get('voting_method', 'early-voting')
    primary_party = data.get('primary_party', '')
    processing_speed = int(data.get('processing_speed', '20'))
    
    # Extract party from election_type if needed
    if election_type == 'primary-democratic':
        primary_party = 'democratic'
        election_type = 'primary'
    elif election_type == 'primary-republican':
        primary_party = 'republican'
        election_type = 'primary'
    
    if not county:
        return jsonify({'error': 'County is required'}), 400
    if not election_type:
        return jsonify({'error': 'Election type is required'}), 400
    if not election_date:
        return jsonify({'error': 'Election date is required'}), 400
    
    created_jobs = []
    errors = []
    
    for url in urls:
        try:
            logger.info(f"Fetching file from URL: {url}")
            
            # Download the file
            resp = req_lib.get(url, timeout=120, stream=True, allow_redirects=True)
            resp.raise_for_status()
            
            # Determine filename from URL or Content-Disposition header
            filename = ''
            cd = resp.headers.get('Content-Disposition', '')
            if 'filename=' in cd:
                filename = cd.split('filename=')[-1].strip('"\'')
            if not filename:
                from urllib.parse import urlparse, unquote
                path = urlparse(url).path
                filename = unquote(path.split('/')[-1]) if path else 'download'
            
            # Ensure valid extension
            lower_fn = filename.lower()
            if not any(lower_fn.endswith(ext) for ext in ['.csv', '.xls', '.xlsx', '.pdf']):
                # Try to guess from content type
                ct = resp.headers.get('Content-Type', '')
                if 'csv' in ct or 'text/plain' in ct:
                    filename += '.csv'
                elif 'excel' in ct or 'spreadsheet' in ct:
                    filename += '.xlsx'
                elif 'pdf' in ct:
                    filename += '.pdf'
                else:
                    filename += '.csv'  # Default to CSV
            
            # Check file size (100MB limit)
            content = resp.content
            if len(content) > 100 * 1024 * 1024:
                errors.append(f"{url}: File exceeds 100MB limit")
                continue
            if len(content) == 0:
                errors.append(f"{url}: Downloaded file is empty")
                continue
            
            # Save to upload directory
            file_id = str(uuid.uuid4())
            from werkzeug.utils import secure_filename
            safe_name = secure_filename(filename) or 'download.csv'
            saved_filename = f"{file_id}_{safe_name}"
            Config.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
            filepath = Config.UPLOAD_DIR / saved_filename
            with open(filepath, 'wb') as f:
                f.write(content)
            
            logger.info(f"Saved URL download: {saved_filename} ({len(content)} bytes)")
            
            # Create processing job
            job_id = str(uuid.uuid4())
            job = ProcessingJob(
                str(filepath),
                year=year,
                county=county,
                election_type=election_type,
                election_date=election_date,
                voting_method=voting_method,
                original_filename=filename,
                primary_party=primary_party,
                job_id=job_id,
                max_workers=processing_speed
            )
            
            with jobs_lock:
                active_jobs[job_id] = job
                job_queue.append(job_id)
            
            created_jobs.append({
                'job_id': job_id,
                'filename': filename,
                'url': url,
                'county': county,
                'year': year,
                'election_type': election_type,
                'status': 'queued',
                'size_bytes': len(content)
            })
            
            logger.info(f"Created job {job_id} for URL {url}")
            
        except req_lib.exceptions.RequestException as e:
            logger.error(f"Failed to fetch URL {url}: {e}")
            errors.append(f"{url}: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to process URL {url}: {e}")
            errors.append(f"{url}: {str(e)}")
    
    # Start processing
    if created_jobs:
        start_job_processor()
        save_jobs_to_disk()
    
    return jsonify({
        'success': len(created_jobs) > 0,
        'jobs': created_jobs,
        'errors': errors
    }), 200 if created_jobs else 400


@app.route('/admin/upload', methods=['POST'])
@require_auth
def upload_csv():
    """Handle multiple CSV file uploads."""
    
    # Check if files were provided
    if 'files' not in request.files and 'file' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    # Get files (support both 'files' for multiple and 'file' for single)
    files = request.files.getlist('files') if 'files' in request.files else [request.files['file']]
    
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files selected'}), 400
    
    # Get duplicate handling action (skip, replace, or ignore)
    duplicate_action = request.form.get('duplicate_action', 'skip')
    
    # Get processing speed (number of workers for parallel geocoding)
    processing_speed = int(request.form.get('processing_speed', '20'))
    
    # Get column mapping if provided (JSON string from the mapping modal)
    column_mapping_str = request.form.get('column_mapping', '')
    column_mapping = {}
    if column_mapping_str:
        try:
            column_mapping = json.loads(column_mapping_str)
        except Exception:
            pass
    
    created_jobs = []
    errors = []
    skipped = []
    
    for file in files:
        if file.filename == '':
            continue
            
        try:
            # Get file info including parsed metadata from filename
            file_info = get_file_info(file)
            
            # Form data can override filename-parsed values
            county = request.form.get('county') or file_info['county']
            year = request.form.get('year') or file_info['year']
            election_type = request.form.get('election_type') or file_info['election_type']
            election_date = request.form.get('election_date') or file_info.get('election_date')
            voting_method = request.form.get('voting_method', 'early-voting')
            primary_party = request.form.get('primary_party', '')
            
            # Extract party from election_type if it's primary-democratic or primary-republican
            if election_type == 'primary-democratic':
                primary_party = 'democratic'
                election_type = 'primary'
            elif election_type == 'primary-republican':
                primary_party = 'republican'
                election_type = 'primary'
            
            # Validate required fields
            if not county or county == 'Unknown':
                errors.append(f"{file.filename}: County is required")
                continue
            
            if not election_type:
                errors.append(f"{file.filename}: Election type is required")
                continue
            
            if not election_date:
                errors.append(f"{file.filename}: Election date is required")
                continue
            
            # Check for duplicates (unless action is 'ignore')
            if duplicate_action != 'ignore':
                import json
                public_data_dir = Config.PUBLIC_DIR / 'data'
                is_duplicate = False
                existing_metadata_file = None
                
                if public_data_dir.exists():
                    for metadata_file in public_data_dir.glob('metadata*.json'):
                        try:
                            with open(metadata_file, 'r') as f:
                                existing = json.load(f)
                            
                            if (existing.get('county') == county and
                                existing.get('year') == year and
                                existing.get('election_type') == election_type and
                                existing.get('election_date') == election_date and
                                existing.get('voting_method') == voting_method):
                                
                                is_duplicate = True
                                existing_metadata_file = metadata_file
                                break
                        except Exception:
                            continue
                
                # Handle duplicate based on action
                if is_duplicate:
                    if duplicate_action == 'skip':
                        skipped.append(f"{file.filename}: Already exists")
                        continue
                    elif duplicate_action == 'replace' and existing_metadata_file:
                        # Delete existing files
                        try:
                            map_data_file = existing_metadata_file.parent / existing_metadata_file.name.replace('metadata', 'map_data')
                            if existing_metadata_file.exists():
                                existing_metadata_file.unlink()
                            if map_data_file.exists():
                                map_data_file.unlink()
                            logger.info(f"Deleted existing dataset for replacement: {existing_metadata_file.name}")
                        except Exception as e:
                            logger.error(f"Failed to delete existing dataset: {e}")
                            errors.append(f"{file.filename}: Failed to delete existing dataset")
                            continue
            
            # Validate file
            is_valid, error_msg = validate_file(file)
            if not is_valid:
                errors.append(f"{file.filename}: {error_msg}")
                continue
            
            # Save file
            filepath = save_upload(file)
            
            # Create job
            job_id = str(uuid.uuid4())
            job = ProcessingJob(
                filepath,
                year=year,
                county=county,
                election_type=election_type,
                election_date=election_date,
                voting_method=voting_method,
                original_filename=file.filename,
                primary_party=primary_party,
                job_id=job_id,
                max_workers=processing_speed,
                column_mapping=column_mapping
            )
            
            # Add to job tracking
            with jobs_lock:
                active_jobs[job_id] = job
                job_queue.append(job_id)
            
            created_jobs.append({
                'job_id': job_id,
                'filename': file.filename,
                'county': county,
                'year': year,
                'election_type': election_type,
                'status': 'queued'
            })
            
            logger.info(f"Created job {job_id} for file {file.filename}")
            
        except Exception as e:
            logger.error(f"Failed to create job for {file.filename}: {e}")
            errors.append(f"{file.filename}: {str(e)}")
    
    # Start processing jobs if not already running
    start_job_processor()
    
    # Save jobs to disk
    save_jobs_to_disk()
    
    response = {
        'success': len(created_jobs) > 0,
        'jobs': created_jobs,
        'errors': errors,
        'skipped': skipped
    }
    
    if len(created_jobs) == 0 and len(skipped) == 0:
        return jsonify(response), 400
    
    return jsonify(response)

@app.route('/admin/upload-state-voter-data', methods=['POST'])
@require_auth
def upload_state_voter_data():
    """Handle Texas Secretary of State voter data file uploads.
    
    These files have limited data (name, VUID, voting method, precinct) and
    no addresses. We tally/deduplicate by VUID and store for future cross-reference.
    No geocoding is performed.
    """
    import csv
    import io
    import database as db
    
    db.init_db()
    
    if 'files' not in request.files:
        return jsonify({'error': 'No files provided'}), 400
    
    files = request.files.getlist('files')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No files selected'}), 400
    
    election_date = request.form.get('election_date', '')
    election_year = request.form.get('election_year', '')
    
    # Parse file metadata from JSON
    file_metadata = []
    try:
        meta_str = request.form.get('file_metadata', '[]')
        file_metadata = json.loads(meta_str)
    except Exception:
        pass
    
    # Build metadata lookup by filename
    meta_lookup = {m['filename']: m for m in file_metadata}
    
    log_lines = []
    def log(msg):
        log_lines.append(msg)
        logger.info(f"[state-upload] {msg}")
    
    log(f"Processing {len(files)} state voter data file(s)")
    
    # Collect all records across all files, keyed by (county, party, vuid) for dedup
    # Structure: { (county, party): { vuid: record } }
    all_voters = {}
    total_records = 0
    duplicates_skipped = 0
    files_processed = 0
    
    for file in files:
        if file.filename == '':
            continue
        
        meta = meta_lookup.get(file.filename, {})
        county = meta.get('county', '')
        party = meta.get('party', '')
        el_type = meta.get('election_type', 'primary')
        voting_method = meta.get('voting_method', 'early-voting')
        file_date = meta.get('file_date', '')
        year = meta.get('year', '') or election_year
        
        # Convert file_date (MM_DD_YYYY) to ISO format (YYYY-MM-DD) for vote_date
        vote_date_iso = ''
        if file_date:
            try:
                parts = file_date.split('_')
                if len(parts) == 3:
                    vote_date_iso = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
            except Exception:
                vote_date_iso = file_date
        
        if not county:
            log(f"⚠️ Skipping {file.filename} — no county detected")
            continue
        
        # Capitalize party for DB storage
        party_voted = ''
        if party == 'democratic':
            party_voted = 'Democratic'
        elif party == 'republican':
            party_voted = 'Republican'
        
        log(f"📄 {file.filename} — {county} County, {party_voted or 'Unknown'} {el_type}, {voting_method}")
        
        # Read CSV content
        try:
            content = file.read().decode('utf-8', errors='replace')
            reader = csv.reader(io.StringIO(content))
            
            # Read header
            header = next(reader, None)
            if not header:
                log(f"  ⚠️ Empty file, skipping")
                continue
            
            # Normalize header
            header_lower = [h.strip().lower().replace('"', '') for h in header]
            
            # Find column indices
            name_idx = None
            vuid_idx = None
            method_idx = None
            precinct_idx = None
            
            for i, h in enumerate(header_lower):
                if h in ('voter_name', 'name', 'voter name'):
                    name_idx = i
                elif h in ('id_voter', 'vuid', 'voter_id', 'voter id'):
                    vuid_idx = i
                elif h in ('voting_method', 'method', 'voting method', 'vote_method'):
                    method_idx = i
                elif h in ('tx_precinct_code', 'precinct', 'precinct_code', 'tx precinct code'):
                    precinct_idx = i
            
            if vuid_idx is None:
                log(f"  ⚠️ No VUID column found, skipping")
                continue
            
            group_key = f"{county}|{party_voted}"
            if group_key not in all_voters:
                all_voters[group_key] = {}
            
            file_count = 0
            file_dups = 0
            for row in reader:
                if len(row) <= vuid_idx:
                    continue
                
                raw_vuid = row[vuid_idx].strip().replace('"', '')
                if not raw_vuid or not raw_vuid.isdigit():
                    continue
                
                total_records += 1
                file_count += 1
                
                # Deduplicate by VUID within this county+party group
                if raw_vuid in all_voters[group_key]:
                    file_dups += 1
                    duplicates_skipped += 1
                    continue
                
                # Parse voter name: "LAST, FIRST MIDDLE"
                firstname = ''
                lastname = ''
                if name_idx is not None and len(row) > name_idx:
                    raw_name = row[name_idx].strip().replace('"', '')
                    if ',' in raw_name:
                        parts = raw_name.split(',', 1)
                        lastname = parts[0].strip()
                        first_parts = parts[1].strip().split()
                        firstname = first_parts[0] if first_parts else ''
                    else:
                        lastname = raw_name
                
                # Parse voting method from CSV data
                row_method = voting_method
                if method_idx is not None and len(row) > method_idx:
                    raw_method = row[method_idx].strip().replace('"', '').upper()
                    if raw_method == 'IN-PERSON':
                        row_method = 'early-voting'
                    elif raw_method == 'MAIL-IN' or raw_method == 'MAIL':
                        row_method = 'mail-in'
                
                # Parse precinct
                precinct = ''
                if precinct_idx is not None and len(row) > precinct_idx:
                    precinct = row[precinct_idx].strip().replace('"', '')
                
                all_voters[group_key][raw_vuid] = {
                    'vuid': raw_vuid,
                    'firstname': firstname,
                    'lastname': lastname,
                    'county': county,
                    'party_voted': party_voted,
                    'election_type': el_type,
                    'voting_method': row_method,
                    'precinct': precinct,
                    'year': year,
                    'source_file': file.filename,
                    'vote_date': vote_date_iso,
                }
            
            log(f"  ✅ {file_count} records, {file_dups} duplicates within file")
            files_processed += 1
            
        except Exception as e:
            log(f"  ❌ Error reading file: {e}")
            continue
    
    # Now write all deduplicated voters to the database
    log(f"\nWriting to database...")
    
    total_unique = 0
    per_county = {}
    
    for group_key, voters in all_voters.items():
        county, party_voted = group_key.split('|')
        voter_list = list(voters.values())
        total_unique += len(voter_list)
        
        # Track per-county stats
        if group_key not in per_county:
            per_county[group_key] = {
                'unique_voters': 0,
                'voting_methods': set()
            }
        per_county[group_key]['unique_voters'] = len(voter_list)
        per_county[group_key]['voting_methods'].update(
            set(v['voting_method'] for v in voter_list)
        )
        
        log(f"  {county} — {party_voted}: {len(voter_list):,} unique voters")
        
        # Batch record election participation
        election_batch = []
        voter_batch = []
        
        for v in voter_list:
            election_batch.append({
                'vuid': v['vuid'],
                'election_date': election_date,
                'election_year': v['year'],
                'election_type': v['election_type'],
                'voting_method': v['voting_method'],
                'party_voted': v['party_voted'],
                'precinct': v['precinct'],
                'ballot_style': '',
                'site': '',
                'check_in': '',
                'source_file': v['source_file'],
                'vote_date': v.get('vote_date', ''),
                'data_source': 'state-voter-data',
            })
            
            voter_batch.append({
                'vuid': v['vuid'],
                'lastname': v['lastname'],
                'firstname': v['firstname'],
                'middlename': '',
                'suffix': '',
                'address': '',
                'city': '',
                'zip': '',
                'county': v['county'],
                'birth_year': None,
                'registration_date': '',
                'sex': '',
                'registered_party': '',
                'current_party': v['party_voted'],
                'precinct': v['precinct'],
                'lat': None,
                'lng': None,
                'source': 'state-voter-data',
            })
            
            # Batch in chunks of 500
            if len(election_batch) >= 500:
                db.record_elections_batch(election_batch)
                db.upsert_voters_batch(voter_batch)
                election_batch = []
                voter_batch = []
        
        # Flush remaining
        if election_batch:
            db.record_elections_batch(election_batch)
            db.upsert_voters_batch(voter_batch)
        
        log(f"    ✅ Recorded {len(voter_list):,} election records + voter upserts")
    
    # Invalidate cache so new data shows up
    cache_invalidate()
    
    log(f"\n🎉 Done! {total_unique:,} unique voters from {files_processed} files ({duplicates_skipped:,} duplicates skipped)")
    
    # Convert sets to lists for JSON serialization
    per_county_json = {}
    for k, v in per_county.items():
        per_county_json[k] = {
            'unique_voters': v['unique_voters'],
            'voting_methods': list(v['voting_methods'])
        }
    
    return jsonify({
        'success': True,
        'log': log_lines,
        'results': {
            'total_unique_voters': total_unique,
            'total_records_processed': total_records,
            'files_processed': files_processed,
            'duplicates_skipped': duplicates_skipped,
            'per_county': per_county_json,
        }
    })


def start_job_processor():
    """Start the background job processor if not already running."""
    # Check if processor thread is already running
    for thread in threading.enumerate():
        if thread.name == 'job_processor':
            return
    
    # Start new processor thread
    thread = threading.Thread(target=process_job_queue, name='job_processor')
    thread.daemon = True
    thread.start()
    logger.info("Started job processor thread")

def process_job_queue():
    """Background thread that processes jobs from the queue."""
    while True:
        try:
            # Get jobs to process
            jobs_to_run = []
            
            with jobs_lock:
                # Count currently running jobs
                running_count = sum(1 for job in active_jobs.values() if job.status == 'running')
                
                # Get queued jobs that can start
                available_slots = max_concurrent_jobs - running_count
                
                if available_slots > 0 and job_queue:
                    for _ in range(min(available_slots, len(job_queue))):
                        if job_queue:
                            job_id = job_queue.pop(0)
                            if job_id in active_jobs:
                                jobs_to_run.append(active_jobs[job_id])
            
            # Run jobs outside the lock — use a progress-saving wrapper
            for job in jobs_to_run:
                try:
                    logger.info(f"Starting job {job.job_id}")
                    # Start a background thread to periodically save progress to disk
                    stop_saver = threading.Event()
                    saver_thread = threading.Thread(
                        target=_periodic_save, args=(stop_saver,), 
                        name=f'saver_{job.job_id}', daemon=True
                    )
                    saver_thread.start()
                    
                    job.run()
                    logger.info(f"Completed job {job.job_id}")
                    cache_invalidate()  # Clear cached API responses after data changes
                except Exception as e:
                    logger.error(f"Job {job.job_id} failed: {e}")
                finally:
                    stop_saver.set()
                    save_jobs_to_disk()
            
            # Also save periodically even when idle (picks up progress from running jobs)
            save_jobs_to_disk()
            
            # Sleep before checking queue again
            import time
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Job processor error: {e}")
            import time
            time.sleep(5)

def _periodic_save(stop_event):
    """Periodically save job state to disk while a job is running."""
    import time
    while not stop_event.is_set():
        try:
            save_jobs_to_disk()
        except Exception as e:
            logger.error(f"Periodic save error: {e}")
        stop_event.wait(3)  # Save every 3 seconds

@app.route('/admin/status')
@require_auth
def get_status():
    """Get status of all processing jobs.
    
    Always reads from disk first (cross-worker visibility), then merges
    with in-memory state if available (for log_messages which aren't persisted).
    """
    jobs_status = []
    
    # Primary source: disk file (updated every 3s by the worker running the job)
    persisted = load_jobs_from_disk()
    
    # Also check in-memory jobs (same worker only — may have richer data like log_messages)
    in_memory = {}
    with jobs_lock:
        for job_id, job in active_jobs.items():
            cache_hits = job.cache_hits if hasattr(job, 'cache_hits') else 0
            in_memory[job_id] = {
                'job_id': job.job_id,
                'status': job.status,
                'progress': job.progress,
                'total_records': job.total_records,
                'processed_records': job.processed_records,
                'geocoded_count': job.geocoded_count,
                'failed_count': job.failed_count,
                'cache_hits': cache_hits,
                'county': job.county,
                'year': job.year,
                'election_type': job.election_type,
                'voting_method': job.voting_method,
                'primary_party': getattr(job, 'primary_party', ''),
                'is_early_voting': job.voting_method == 'early-voting' and not hasattr(job, '_is_standard_geocode'),
                'original_filename': job.original_filename,
                'log_messages': job.log_messages[-20:] if hasattr(job, 'log_messages') else [],
                'errors': job.errors[:5] if hasattr(job, 'errors') else [],
                'started_at': job.started_at.isoformat() if hasattr(job, 'started_at') and job.started_at else None,
                'completed_at': job.completed_at.isoformat() if hasattr(job, 'completed_at') and job.completed_at else None
            }
    
    # Merge: prefer in-memory (has log_messages), fall back to disk
    seen_ids = set()
    for job_id, mem_job in in_memory.items():
        jobs_status.append(mem_job)
        seen_ids.add(job_id)
    
    for job_id, disk_job in persisted.items():
        if job_id not in seen_ids:
            # Add log_messages/errors as empty lists if not present
            disk_job.setdefault('log_messages', [])
            disk_job.setdefault('errors', [])
            disk_job.setdefault('primary_party', '')
            disk_job.setdefault('is_early_voting', False)
            
            # Auto-complete stale "running" jobs where all records are processed
            # but the worker died before marking completion (e.g. OOM SIGKILL)
            if (disk_job.get('status') == 'running'
                    and disk_job.get('total_records', 0) > 0
                    and disk_job.get('processed_records', 0) >= disk_job.get('total_records', 0)):
                disk_job['status'] = 'completed'
                disk_job['progress'] = 1.0
                if not disk_job.get('completed_at'):
                    from datetime import datetime as _dt
                    disk_job['completed_at'] = _dt.now().isoformat()
                # Persist the fix directly to disk
                try:
                    all_persisted = load_jobs_from_disk()
                    all_persisted[job_id] = disk_job
                    with open(JOBS_FILE, 'w') as _f:
                        json.dump(all_persisted, _f, indent=2)
                except Exception:
                    pass
                logger.info(f"Auto-completed stale job {job_id} (all records processed)")
            
            jobs_status.append(disk_job)
    
    result = {
        'jobs': jobs_status,
        'queue_length': sum(1 for j in jobs_status if j.get('status') == 'queued'),
        'active_count': sum(1 for j in jobs_status if j.get('status') == 'running')
    }
    
    # Add flat fields from most recent active/running job for backward compatibility
    active_jobs_list = [j for j in jobs_status if j.get('status') in ('running', 'queued')]
    latest_list = active_jobs_list if active_jobs_list else jobs_status
    
    if latest_list:
        latest = latest_list[-1]
        result['status'] = latest.get('status', 'idle')
        result['total_records'] = latest.get('total_records', 0)
        result['processed_records'] = latest.get('processed_records', 0)
        result['geocoded_count'] = latest.get('geocoded_count', 0)
        result['failed_count'] = latest.get('failed_count', 0)
        result['cache_hits'] = latest.get('cache_hits', 0)
        result['log_messages'] = latest.get('log_messages', [])
        result['errors'] = latest.get('errors', [])
        result['progress'] = latest.get('progress', 0)
    else:
        result['status'] = 'idle'
    
    return jsonify(result)

@app.route('/admin/job/<job_id>')
@require_auth
def get_job_status(job_id):
    """Get status of a specific job."""
    with jobs_lock:
        if job_id not in active_jobs:
            return jsonify({'error': 'Job not found'}), 404
        
        job = active_jobs[job_id]
        # Use job.cache_hits instead of geocoder stats
        cache_hits = job.cache_hits if hasattr(job, 'cache_hits') else 0
        
        return jsonify({
            'job_id': job.job_id,
            'status': job.status,
            'progress': job.progress,
            'total_records': job.total_records,
            'processed_records': job.processed_records,
            'geocoded_count': job.geocoded_count,
            'failed_count': job.failed_count,
            'cache_hits': cache_hits,
            'county': job.county,
            'year': job.year,
            'election_type': job.election_type,
            'voting_method': job.voting_method,
            'original_filename': job.original_filename,
            'log_messages': job.log_messages[-50:] if hasattr(job, 'log_messages') else [],
            'errors': job.errors[:10] if hasattr(job, 'errors') else [],
            'started_at': job.started_at.isoformat() if hasattr(job, 'started_at') and job.started_at else None,
            'completed_at': job.completed_at.isoformat() if hasattr(job, 'completed_at') and job.completed_at else None,
            'integrity_report': job.integrity_report if hasattr(job, 'integrity_report') else None
        })

@app.route('/admin/download/errors')
@require_auth
def download_errors():
    """Download error CSV file."""
    error_file = Config.DATA_DIR / 'processing_errors.csv'
    if error_file.exists():
        return send_from_directory(Config.DATA_DIR, 'processing_errors.csv', as_attachment=True)
    return jsonify({'error': 'No error file available'}), 404

@app.route('/admin/regeocode', methods=['POST'])
@require_auth
def regeocode_data():
    """Re-geocode existing data from map_data file."""
    global current_job
    
    data = request.get_json()
    map_data_file = data.get('map_data_file')
    county = data.get('county')
    year = data.get('year')
    election_type = data.get('election_type')
    election_date = data.get('election_date')
    voting_method = data.get('voting_method', 'early-voting')
    
    if not map_data_file:
        return jsonify({'error': 'Map data file is required'}), 400
    
    # Check if another job is running
    with job_lock:
        if current_job and current_job.status == 'running':
            return jsonify({'error': 'Another job is already running'}), 409
        
        # Load the existing map_data file
        map_data_path = Config.PUBLIC_DIR / 'data' / map_data_file
        
        if not map_data_path.exists():
            return jsonify({'error': f'Map data file not found: {map_data_file}'}), 404
        
        try:
            import json
            import pandas as pd
            from pathlib import Path
            
            # Read the GeoJSON file
            with open(map_data_path, 'r', encoding='utf-8') as f:
                geojson_data = json.load(f)
            
            # Extract addresses from features
            addresses = []
            for feature in geojson_data.get('features', []):
                props = feature['properties']
                addresses.append({
                    'ADDRESS': props.get('original_address', props.get('address', '')),
                    'PRECINCT': props.get('precinct', ''),
                    'BALLOT STYLE': props.get('ballot_style', ''),
                    'ID': props.get('id', ''),
                    'VUID': props.get('vuid', ''),
                    'CERT': props.get('cert', ''),
                    'LASTNAME': props.get('lastname', ''),
                    'FIRSTNAME': props.get('firstname', ''),
                    'MIDDLENAME': props.get('middlename', ''),
                    'SUFFIX': props.get('suffix', ''),
                    'CHECK-IN': props.get('check_in', ''),
                    'SITE': props.get('site', ''),
                    'PARTY': props.get('party', '')
                })
            
            # Create a temporary CSV file
            temp_csv_path = Config.UPLOAD_DIR / f'regeocode_{map_data_file.replace(".json", ".csv")}'
            df = pd.DataFrame(addresses)
            df.to_csv(temp_csv_path, index=False)
            
            # Create and start processing job
            current_job = ProcessingJob(
                str(temp_csv_path),
                year=year,
                county=county,
                election_type=election_type,
                election_date=election_date,
                voting_method=voting_method,
                original_filename=f'Re-geocode: {map_data_file}'
            )
            thread = threading.Thread(target=current_job.run)
            thread.daemon = True
            thread.start()
            
            return jsonify({
                'success': True,
                'job_id': current_job.job_id,
                'message': f'Re-geocoding {len(addresses)} addresses'
            })
            
        except Exception as e:
            logger.error(f"Re-geocoding failed: {e}")
            return jsonify({'error': f'Failed to process map data: {str(e)}'}), 500

@app.route('/admin/list-datasets', methods=['GET'])
def list_datasets():
    """List all available datasets by scanning for metadata files."""
    try:
        import json
        
        datasets = []
        seen_datasets = set()  # Track unique datasets by key attributes
        public_data_dir = Config.PUBLIC_DIR / 'data'
        
        # Find all metadata files
        if public_data_dir.exists():
            for metadata_file in public_data_dir.glob('metadata*.json'):
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                    
                    # Create a unique key for this dataset (include party for primaries, early vote day for snapshots)
                    dataset_key = (
                        metadata.get('county', 'Unknown'),
                        metadata.get('year', 'Unknown'),
                        metadata.get('election_type', 'Unknown'),
                        metadata.get('election_date', 'Unknown'),
                        metadata.get('voting_method', 'Unknown'),
                        metadata.get('primary_party', ''),  # Include party to distinguish DEM/REP primaries
                        metadata.get('early_vote_day', ''),  # Include day for early vote snapshots
                        metadata.get('is_cumulative', False)  # Distinguish cumulative from snapshots
                    )
                    
                    # Skip if we've already seen this dataset
                    if dataset_key in seen_datasets:
                        logger.debug(f"Skipping duplicate dataset: {metadata_file.name}")
                        continue
                    
                    seen_datasets.add(dataset_key)
                    
                    # Derive map_data filename from metadata filename
                    map_data_file = metadata_file.name.replace('metadata', 'map_data')
                    
                    datasets.append({
                        'metadataFile': metadata_file.name,
                        'mapDataFile': map_data_file,
                        'county': metadata.get('county', 'Unknown'),
                        'year': metadata.get('year', 'Unknown'),
                        'electionType': metadata.get('election_type', 'Unknown'),
                        'electionDate': metadata.get('election_date', 'Unknown'),
                        'votingMethod': metadata.get('voting_method', 'Unknown'),
                        'primaryParty': metadata.get('primary_party', ''),  # Include party for primaries
                        'lastUpdated': metadata.get('last_updated', ''),
                        'totalAddresses': metadata.get('total_addresses', 0),
                        'rawVoterCount': metadata.get('raw_voter_count', metadata.get('total_addresses', 0)),
                        'originalFilename': metadata.get('original_filename', ''),
                        'isEarlyVoting': metadata.get('is_early_voting', False),
                        'isCumulative': metadata.get('is_cumulative', False),
                        'earlyVoteDay': metadata.get('early_vote_day', '')
                    })
                except Exception as e:
                    logger.warning(f"Could not read metadata file {metadata_file.name}: {e}")
                    continue
        
        # Sort by election date (most recent first)
        datasets.sort(key=lambda d: d.get('electionDate', ''), reverse=True)
        
        logger.info(f"Found {len(datasets)} unique datasets")
        
        return jsonify({
            'success': True,
            'datasets': datasets
        })
        
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}")
        return jsonify({'error': f'Failed to list datasets: {str(e)}'}), 500

@app.route('/admin/delete', methods=['POST'])
@require_auth
def delete_data():
    """Delete map data and metadata files."""
    data = request.get_json()
    map_data_file = data.get('map_data_file')
    metadata_file = data.get('metadata_file')
    
    if not map_data_file or not metadata_file:
        return jsonify({'error': 'Both map_data_file and metadata_file are required'}), 400
    
    try:
        import os
        
        deleted_files = []
        errors = []
        
        # Delete from public/data directory
        public_map_path = Config.PUBLIC_DIR / 'data' / map_data_file
        public_metadata_path = Config.PUBLIC_DIR / 'data' / metadata_file
        
        if public_map_path.exists():
            os.remove(public_map_path)
            deleted_files.append(str(public_map_path))
        
        if public_metadata_path.exists():
            os.remove(public_metadata_path)
            deleted_files.append(str(public_metadata_path))
        
        # Delete from backend data directory
        backend_map_path = Config.DATA_DIR / map_data_file
        backend_metadata_path = Config.DATA_DIR / metadata_file
        
        if backend_map_path.exists():
            os.remove(backend_map_path)
            deleted_files.append(str(backend_map_path))
        
        if backend_metadata_path.exists():
            os.remove(backend_metadata_path)
            deleted_files.append(str(backend_metadata_path))
        
        if not deleted_files:
            return jsonify({'error': 'No files found to delete'}), 404
        
        logger.info(f"Deleted files: {deleted_files}")
        
        return jsonify({
            'success': True,
            'deleted_files': deleted_files,
            'message': f'Deleted {len(deleted_files)} files'
        })
        
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        return jsonify({'error': f'Failed to delete files: {str(e)}'}), 500

# --- Rescan endpoint: reprocess flips + re-resolve unmatched VUIDs ---
RESCAN_FILE = Config.DATA_DIR / 'rescan_status.json'

def _read_rescan_status():
    if RESCAN_FILE.exists():
        try:
            with open(RESCAN_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {'running': False, 'result': None}

def _write_rescan_status(status):
    with open(RESCAN_FILE, 'w') as f:
        json.dump(status, f)

@app.route('/admin/rescan', methods=['POST'])
@require_auth
def rescan_datasets():
    """Rescan all datasets to reprocess flipped voters and re-resolve unmatched VUIDs."""
    st = _read_rescan_status()
    if st.get('running'):
        return jsonify({'error': 'A rescan is already running'}), 409

    _write_rescan_status({'running': True, 'result': None})

    def _run_rescan():
        try:
            data_dir = Config.DATA_DIR
            public_data_dir = Config.PUBLIC_DIR / 'data'
            summary = {'datasets_scanned': 0, 'total_flips': 0, 'vuids_resolved': 0}

            metadata_files = sorted(data_dir.glob('metadata_*.json'))
            logger.info(f"[Rescan] Found {len(metadata_files)} metadata files")

            for meta_path in metadata_files:
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    county = meta.get('county', '')
                    election_date = meta.get('election_date', '')
                    if not county or not election_date:
                        continue

                    map_data_name = 'map_data_' + meta_path.name[len('metadata_'):]
                    map_data_path = data_dir / map_data_name
                    if not map_data_path.exists():
                        continue

                    with open(map_data_path) as f:
                        geojson = json.load(f)
                    features = geojson.get('features', [])
                    if not features:
                        continue

                    engine = CrossReferenceEngine(county, election_date, data_dir)
                    earlier = engine.find_earlier_datasets()

                    if not earlier:
                        for feature in features:
                            feature['properties']['party_affiliation_previous'] = ''
                    else:
                        merged_vuid = {}
                        merged_name_coord = {}
                        for ds in earlier:
                            if not ds['map_data_path'].exists():
                                continue
                            lookups = engine.load_voter_lookup(ds['map_data_path'])
                            for k, v in lookups['vuid_lookup'].items():
                                if k not in merged_vuid:
                                    merged_vuid[k] = v
                            for k, v in lookups['name_coord_lookup'].items():
                                if k not in merged_name_coord:
                                    merged_name_coord[k] = v

                        flips = 0
                        for feature in features:
                            props = feature['properties']
                            coords = feature.get('geometry', {}).get('coordinates', [])
                            voter_row = {
                                'vuid': str(props.get('vuid', '')),
                                'lastname': str(props.get('lastname', '')),
                                'firstname': str(props.get('firstname', '')),
                                'lat': coords[1] if len(coords) >= 2 else 0,
                                'lng': coords[0] if len(coords) >= 2 else 0,
                                'party_affiliation_current': props.get('party_affiliation_current', ''),
                                'ballot_style': props.get('ballot_style', ''),
                                'party': props.get('party', ''),
                            }
                            prev_party = engine.get_previous_party(voter_row, merged_vuid, merged_name_coord)
                            props['party_affiliation_previous'] = prev_party
                            if prev_party:
                                flips += 1

                        summary['total_flips'] += flips

                    with open(map_data_path, 'w') as f:
                        json.dump(geojson, f)
                    pub_path = public_data_dir / map_data_name
                    if public_data_dir.exists():
                        with open(pub_path, 'w') as f:
                            json.dump(geojson, f)

                    summary['datasets_scanned'] += 1
                    logger.info(f"[Rescan] Processed {map_data_name}: {flips if earlier else 0} flips")
                except Exception as e:
                    logger.warning(f"[Rescan] Error processing {meta_path.name}: {e}")

            # PART 2: Re-resolve unmatched VUIDs
            from vuid_resolver import VUIDResolver
            counties = set()
            for meta_path in metadata_files:
                try:
                    with open(meta_path) as f:
                        meta = json.load(f)
                    c = meta.get('county', '')
                    if c:
                        counties.add(c)
                except Exception:
                    pass

            for county in counties:
                try:
                    resolver = VUIDResolver(county, data_dir)
                    resolver.build_lookup()
                    if not resolver.vuid_lookup:
                        continue

                    for filepath in data_dir.glob(f'map_data_{county}_*.json'):
                        try:
                            with open(filepath) as f:
                                data_content = json.load(f)
                            features = data_content.get('features', [])
                            updated = 0
                            for feature in features:
                                props = feature.get('properties', {})
                                if not props.get('unmatched', False):
                                    continue
                                vuid = props.get('vuid', '')
                                if not vuid:
                                    continue
                                match = resolver.resolve(vuid)
                                if match and match.get('lat') is not None:
                                    feature['geometry'] = {
                                        'type': 'Point',
                                        'coordinates': [match['lng'], match['lat']]
                                    }
                                    props['address'] = match['address']
                                    props['display_name'] = match['display_name']
                                    props['unmatched'] = False
                                    updated += 1

                            if updated > 0:
                                with open(filepath, 'w') as f:
                                    json.dump(data_content, f)
                                meta_name = filepath.name.replace('map_data_', 'metadata_')
                                mp = data_dir / meta_name
                                if mp.exists():
                                    with open(mp) as f:
                                        meta = json.load(f)
                                    meta['matched_vuids'] = sum(1 for feat in features if not feat.get('properties', {}).get('unmatched', False))
                                    meta['unmatched_vuids'] = sum(1 for feat in features if feat.get('properties', {}).get('unmatched', False))
                                    meta['last_updated'] = datetime.now().isoformat()
                                    with open(mp, 'w') as f:
                                        json.dump(meta, f, indent=2)
                                import shutil
                                if public_data_dir.exists():
                                    shutil.copy2(filepath, public_data_dir / filepath.name)
                                    if mp.exists():
                                        shutil.copy2(mp, public_data_dir / meta_name)
                                summary['vuids_resolved'] += updated
                                logger.info(f"[Rescan] Re-resolved {updated} VUIDs in {filepath.name}")
                        except Exception as e:
                            logger.warning(f"[Rescan] Error re-resolving {filepath}: {e}")
                except Exception as e:
                    logger.warning(f"[Rescan] Error building VUID lookup for {county}: {e}")

            _write_rescan_status({'running': False, 'result': summary})
            logger.info(f"[Rescan] Complete: {summary}")
        except Exception as e:
            logger.error(f"[Rescan] Failed: {e}")
            _write_rescan_status({'running': False, 'result': {'error': str(e)}})

    thread = threading.Thread(target=_run_rescan, daemon=True)
    thread.start()
    return jsonify({'success': True, 'message': 'Rescan started'})



@app.route('/admin/rescan-status')
@require_auth
def rescan_status_endpoint():
    """Check rescan progress."""
    return jsonify(_read_rescan_status())


# --- Voter Registry Upload ---
REGISTRY_STATUS_FILE = Config.DATA_DIR / 'registry_import_status.json'

def _read_registry_status():
    if REGISTRY_STATUS_FILE.exists():
        try:
            with open(REGISTRY_STATUS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass
    return {'running': False, 'result': None}

def _write_registry_status(status):
    try:
        with open(REGISTRY_STATUS_FILE, 'w') as f:
            json.dump(status, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write registry status: {e}")

@app.route('/admin/upload-registry', methods=['POST'])
@require_auth
def upload_registry():
    """Upload a voter registration file for import into the database."""
    st = _read_registry_status()
    if st.get('running'):
        return jsonify({'error': 'A registry import is already running'}), 409
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    county = request.form.get('county', 'Hidalgo')
    
    # Save the file
    filepath = save_upload(file)
    
    _write_registry_status({
        'running': True,
        'progress': 0,
        'total_records': 0,
        'processed_records': 0,
        'imported_count': 0,
        'status': 'starting',
        'filename': file.filename,
        'county': county,
        'log_messages': []
    })
    
    def _run_import():
        from registry_import import RegistryImportJob
        job = RegistryImportJob(filepath, county=county)
        try:
            # Override log to also write to status file
            original_log = job.log
            def _log_and_persist(message):
                original_log(message)
                _write_registry_status({
                    'running': job.status == 'running',
                    'progress': job.progress,
                    'total_records': job.total_records,
                    'processed_records': job.processed_records,
                    'imported_count': job.imported_count,
                    'status': job.status,
                    'filename': job.original_filename,
                    'county': county,
                    'log_messages': job.log_messages[-20:]
                })
            job.log = _log_and_persist
            
            job.run()
            
            _write_registry_status({
                'running': False,
                'progress': 1.0,
                'total_records': job.total_records,
                'processed_records': job.processed_records,
                'imported_count': job.imported_count,
                'status': 'completed',
                'filename': job.original_filename,
                'county': county,
                'log_messages': job.log_messages[-20:]
            })
        except Exception as e:
            logger.error(f"Registry import failed: {e}")
            _write_registry_status({
                'running': False,
                'status': 'failed',
                'error': str(e),
                'filename': job.original_filename,
                'county': county,
                'log_messages': job.log_messages[-20:]
            })
    
    thread = threading.Thread(target=_run_import, daemon=True)
    thread.start()
    return jsonify({'success': True, 'message': f'Registry import started for {county} County'})


@app.route('/admin/registry-status')
@require_auth
def registry_status_endpoint():
    """Check registry import progress."""
    return jsonify(_read_registry_status())


@app.route('/admin/voter-stats')
@require_auth
def voter_stats_endpoint():
    """Get voter database statistics."""
    county = request.args.get('county')
    stats = db.get_voter_stats(county)
    return jsonify(stats)


@app.route('/admin/county-registries')
@require_auth
def county_registries_endpoint():
    """Get list of counties with voter registries."""
    registries = db.get_county_registries()
    return jsonify(registries)


@app.route('/admin/election-datasets')
@require_auth
def election_datasets_endpoint():
    """Get election datasets from the DB — replaces metadata JSON scanning."""
    county = request.args.get('county')
    datasets = db.get_election_datasets(county)
    return jsonify(datasets)


@app.route('/admin/election-summary')
@require_auth
def election_summary_endpoint():
    """Get high-level election summary including flip/flip-flop counts."""
    summary = db.get_election_summary()
    return jsonify(summary)


# --- Registry Geocoding ---
GEOCODE_REGISTRY_STATUS_FILE = Config.DATA_DIR / 'geocode_registry_status.json'

def start_geocode_registry():
    """Start batch geocoding of ungeocoded voter addresses."""
    # Check if already running
    if GEOCODE_REGISTRY_STATUS_FILE.exists():
        try:
            with open(GEOCODE_REGISTRY_STATUS_FILE, 'r') as f:
                st = json.load(f)
            if st.get('running'):
                return jsonify({'error': 'Geocoding is already running'}), 409
        except Exception:
            pass

    county = request.json.get('county', 'Hidalgo') if request.is_json else 'Hidalgo'
    max_workers = request.json.get('max_workers', 10) if request.is_json else 10

    def _run():
        import subprocess
        result = subprocess.run([
            '/opt/whovoted/venv/bin/python',
            '/opt/whovoted/deploy/geocode_registry.py',
            '--county', county,
            '--batch-size', '100',
            '--max-workers', str(max_workers)
        ])
        # Rebuild static cache after geocoding adds new coordinates
        if result.returncode == 0:
            cache_invalidate()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return jsonify({'success': True, 'message': f'Geocoding started for {county} County'})



@app.route('/admin/geocode-registry-status')
@require_auth
def geocode_registry_status():
    """Check geocoding progress."""
    if GEOCODE_REGISTRY_STATUS_FILE.exists():
        try:
            with open(GEOCODE_REGISTRY_STATUS_FILE, 'r') as f:
                return jsonify(json.load(f))
        except Exception:
            pass
    return jsonify({'running': False})


@app.route('/api/voter/<vuid>')
def voter_profile(vuid):
    """Get full voter profile with election history."""
    voter = db.get_voter_with_elections(vuid)
    if not voter:
        return jsonify({'error': 'Voter not found'}), 404
    return jsonify(voter)


@app.after_request
def set_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://unpkg.com https://www.googletagmanager.com https://www.google-analytics.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://unpkg.com https://fonts.googleapis.com; "
        "font-src 'self' data: https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
        "img-src 'self' data: https: http:; "
        "connect-src 'self' https://nominatim.openstreetmap.org https://*.tile.openstreetmap.org https://*.basemaps.cartocdn.com https://cdnjs.cloudflare.com https://unpkg.com https://www.google-analytics.com https://www.googletagmanager.com"
    )
    return response

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors."""
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

@app.route('/admin/integrity-check', methods=['POST'])
@require_auth
def integrity_check():
    """Run integrity checks on a deployed dataset."""
    try:
        from integrity import verify_ev_upload
        data = request.get_json() or {}
        county = data.get('county', 'Hidalgo')
        year = data.get('year', '2026')
        election_type = data.get('election_type', 'primary')
        election_date = data.get('election_date', '2026-03-03')
        party = data.get('party', '')

        party_suffix = f'_{party}' if party else ''
        date_str = election_date.replace('-', '')

        # Read counts from existing metadata
        meta_file = Config.DATA_DIR / f'metadata_{county}_{year}_{election_type}{party_suffix}_{date_str}_ev.json'
        cum_meta_file = Config.DATA_DIR / f'metadata_{county}_{year}_{election_type}{party_suffix}_cumulative_ev.json'

        raw_count = 0
        cleaned_count = 0
        geocoded = 0
        unmatched_ct = 0

        for mf in [meta_file, cum_meta_file]:
            if mf.exists():
                with open(mf) as f:
                    meta = json.load(f)
                raw_count = meta.get('raw_voter_count', meta.get('total_addresses', 0))
                cleaned_count = meta.get('total_addresses', 0)
                geocoded = meta.get('matched_vuids', 0)
                unmatched_ct = meta.get('unmatched_vuids', 0)
                break

        # Read snapshot to get normalized VUID count
        snap_file = Config.DATA_DIR / f'map_data_{county}_{year}_{election_type}{party_suffix}_{date_str}_ev.json'
        norm_count = cleaned_count
        if snap_file.exists():
            with open(snap_file) as f:
                snap = json.load(f)
            norm_count = len(snap.get('features', []))

        report = verify_ev_upload(
            db_path=str(Config.DATA_DIR / 'whovoted.db'),
            data_dir=Config.DATA_DIR,
            public_dir=Config.PUBLIC_DIR,
            county=county,
            year=year,
            election_type=election_type,
            election_date=election_date,
            party=party,
            raw_row_count=raw_count,
            cleaned_row_count=cleaned_count,
            normalized_vuid_count=norm_count,
            geocoded_count=geocoded,
            unmatched_count=unmatched_ct,
            job_id='manual-check',
            source_file='on-demand',
        )
        return jsonify(report.to_dict())
    except Exception as e:
        logger.error(f"Integrity check error: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# EVR SCRAPER ADMIN ENDPOINTS
# ============================================================================

EVR_SCRAPER_PATH = Path(__file__).parent.parent / 'deploy' / 'evr_scraper.py'
EVR_CRON_CONFIG = Config.DATA_DIR / 'evr_cron_config.json'
EVR_SCRAPER_STATUS = {}  # in-memory status for current/last run
_evr_lock = threading.Lock()


@app.route('/admin/evr-scraper/run', methods=['POST'])
@require_auth
def evr_scraper_run():
    """Manually trigger the EVR scraper."""
    with _evr_lock:
        if EVR_SCRAPER_STATUS.get('running'):
            return jsonify({'error': 'Scraper is already running'}), 409
        EVR_SCRAPER_STATUS['running'] = True
        EVR_SCRAPER_STATUS['started_at'] = datetime.now().isoformat()
        EVR_SCRAPER_STATUS['output'] = ''
        EVR_SCRAPER_STATUS['exit_code'] = None

    def run_scraper_thread():
        import subprocess
        try:
            python = '/opt/whovoted/venv/bin/python3'
            script = '/opt/whovoted/deploy/evr_scraper.py'
            result = subprocess.run(
                [python, script],
                capture_output=True, text=True, timeout=600
            )
            with _evr_lock:
                EVR_SCRAPER_STATUS['output'] = result.stdout + result.stderr
                EVR_SCRAPER_STATUS['exit_code'] = result.returncode
                EVR_SCRAPER_STATUS['finished_at'] = datetime.now().isoformat()
                EVR_SCRAPER_STATUS['running'] = False
            # Invalidate cache so new data shows up
            if result.returncode == 0:
                cache_invalidate()
        except Exception as e:
            with _evr_lock:
                EVR_SCRAPER_STATUS['output'] = str(e)
                EVR_SCRAPER_STATUS['exit_code'] = -1
                EVR_SCRAPER_STATUS['finished_at'] = datetime.now().isoformat()
                EVR_SCRAPER_STATUS['running'] = False

    thread = threading.Thread(target=run_scraper_thread, name='evr_scraper_manual')
    thread.daemon = True
    thread.start()
    return jsonify({'success': True, 'message': 'Scraper started'})


@app.route('/admin/evr-scraper/status')
@require_auth
def evr_scraper_status():
    """Get EVR scraper status and state file info."""
    with _evr_lock:
        status = dict(EVR_SCRAPER_STATUS)

    # Read state file for processed dates info
    state_file = Config.DATA_DIR / 'evr_scraper_state.json'
    state = {}
    if state_file.exists():
        try:
            state = json.loads(state_file.read_text())
        except Exception:
            pass

    # Read scraper log tail
    log_file = Config.DATA_DIR / 'evr_scraper.log'
    log_tail = ''
    if log_file.exists():
        try:
            lines = log_file.read_text().splitlines()
            log_tail = '\n'.join(lines[-50:])
        except Exception:
            pass

    return jsonify({
        'status': status,
        'state': state,
        'log_tail': log_tail,
    })


@app.route('/admin/evr-scraper/cron', methods=['GET', 'POST'])
@require_auth
def evr_scraper_cron():
    """Get or update the EVR scraper cron schedule."""
    if request.method == 'GET':
        config = {'hours': '6,12,18,23', 'enabled': True}
        if EVR_CRON_CONFIG.exists():
            try:
                config = json.loads(EVR_CRON_CONFIG.read_text())
            except Exception:
                pass
        return jsonify(config)

    # POST — update cron
    data = request.get_json() or {}
    hours = data.get('hours', '6,12,18,23')
    enabled = data.get('enabled', True)

    config = {'hours': hours, 'enabled': enabled}
    EVR_CRON_CONFIG.write_text(json.dumps(config, indent=2))

    # Update the actual crontab
    import subprocess
    try:
        cron_line = f"0 {hours} * * * /opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/evr_scraper.py >> /opt/whovoted/data/evr_scraper.log 2>&1"

        if enabled:
            # Remove old EVR cron entries and add new one
            result = subprocess.run(
                ['bash', '-c', f'(crontab -l 2>/dev/null | grep -v evr_scraper; echo "{cron_line}") | crontab -'],
                capture_output=True, text=True, timeout=10
            )
        else:
            # Remove EVR cron entries
            result = subprocess.run(
                ['bash', '-c', 'crontab -l 2>/dev/null | grep -v evr_scraper | crontab -'],
                capture_output=True, text=True, timeout=10
            )

        return jsonify({'success': True, 'config': config, 'cron_output': result.stderr})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/evr-scraper/reset', methods=['POST'])
@require_auth
def evr_scraper_reset():
    """Reset scraper state to re-download all dates."""
    state_file = Config.DATA_DIR / 'evr_scraper_state.json'
    if state_file.exists():
        state_file.unlink()
    return jsonify({'success': True, 'message': 'Scraper state reset. Next run will re-download all dates.'})


# Cleanup old uploads on startup
cleanup_old_uploads()

# Resume queued jobs from disk (handles multi-worker orphaned jobs)
def resume_queued_jobs():
    """On startup, pick up any queued jobs from disk and re-queue them."""
    persisted = load_jobs_from_disk()
    resumed = 0
    for job_id, jdata in persisted.items():
        if jdata.get('status') != 'queued':
            continue
        csv_path = jdata.get('csv_path', '')
        if not csv_path or not os.path.exists(csv_path):
            logger.warning(f"Cannot resume job {job_id[:8]}: file not found ({csv_path})")
            # Mark as failed on disk
            jdata['status'] = 'failed'
            jdata['errors'] = [{'row': 0, 'message': 'Upload file not found on restart'}]
            continue
        try:
            job = ProcessingJob(
                csv_path,
                year=jdata.get('year'),
                county=jdata.get('county'),
                election_type=jdata.get('election_type'),
                election_date=jdata.get('election_date'),
                voting_method=jdata.get('voting_method'),
                original_filename=jdata.get('original_filename'),
                primary_party=jdata.get('primary_party'),
                job_id=job_id,
                max_workers=jdata.get('max_workers', 20)
            )
            with jobs_lock:
                active_jobs[job_id] = job
                job_queue.append(job_id)
            resumed += 1
            logger.info(f"Resumed queued job {job_id[:8]}: {jdata.get('original_filename', '')}")
        except Exception as e:
            logger.error(f"Failed to resume job {job_id[:8]}: {e}")
    
    if resumed > 0:
        thread = threading.Thread(target=process_job_queue, name='job_processor_resume')
        thread.daemon = True
        thread.start()
        logger.info(f"Resumed {resumed} queued job(s)")
    
    # Save any status changes (failed jobs)
    save_jobs_to_disk()

resume_queued_jobs()


def _warmup_cache():
    """Pre-populate in-memory cache for the default dataset on startup.
    
    The file-based cache handles instant cold starts. This warmup populates
    the in-memory cache so subsequent requests (after file cache expires) are fast.
    """
    import time as _t
    _t.sleep(3)  # Let gunicorn workers settle
    try:
        logger.info("Cache warmup: starting...")
        t0 = _t.time()
        
        hm_key = "heatmap:Hidalgo:2026-03-03:early-voting"
        if cache_get(hm_key) is None:
            import json as _json
            points = db.get_voters_heatmap('Hidalgo', '2026-03-03', 'early-voting')
            json_str = _json.dumps({'points': points, 'count': len(points)})
            cache_set(hm_key, json_str)
            logger.info(f"Cache warmup: heatmap cached ({len(points)} points) in {_t.time()-t0:.1f}s")
        
        stats_key = "stats:Hidalgo:2026-03-03:None:early-voting"
        if cache_get(stats_key) is None:
            t1 = _t.time()
            stats = db.get_election_stats('Hidalgo', '2026-03-03', None, 'early-voting')
            response_data = {'success': True, 'stats': stats}
            cache_set(stats_key, response_data)
            logger.info(f"Cache warmup: stats cached in {_t.time()-t1:.1f}s")
        
        logger.info(f"Cache warmup: complete in {_t.time()-t0:.1f}s total")
    except Exception as e:
        logger.error(f"Cache warmup failed: {e}")

# Start warmup in background thread
threading.Thread(target=_warmup_cache, name='cache-warmup', daemon=True).start()


if __name__ == '__main__':
    logger.info("Starting WhoVoted backend server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
