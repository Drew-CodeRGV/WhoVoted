"""Main Flask application for WhoVoted backend."""
from flask import Flask, request, jsonify, send_from_directory, redirect, make_response
from flask_cors import CORS
import logging
import threading
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from config import Config, setup_logging
from auth import authenticate, create_session, validate_session, invalidate_session, require_auth
from upload import validate_file, save_upload, get_file_info, cleanup_old_uploads
from processor import ProcessingJob

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Validate configuration
Config.validate()

# Setup logging
logger = setup_logging()

# Configure CORS
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

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
    """Save job history to disk."""
    try:
        JOBS_FILE.parent.mkdir(parents=True, exist_ok=True)
        jobs_data = {}
        
        with jobs_lock:
            for job_id, job in active_jobs.items():
                # Use job.cache_hits instead of geocoder stats
                cache_hits = job.cache_hits if hasattr(job, 'cache_hits') else 0
                
                jobs_data[job_id] = {
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
                    'started_at': job.started_at.isoformat() if hasattr(job, 'started_at') and job.started_at else None,
                    'completed_at': job.completed_at.isoformat() if hasattr(job, 'completed_at') and job.completed_at else None,
                    'errors': job.errors[:5] if hasattr(job, 'errors') else []
                }
        
        with open(JOBS_FILE, 'w') as f:
            json.dump(jobs_data, f, indent=2)
            
    except Exception as e:
        logger.error(f"Failed to save jobs to disk: {e}")

@app.route('/')
def index():
    """Serve the main public map page."""
    return send_from_directory(Config.PUBLIC_DIR, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    """Serve static files from public directory."""
    try:
        return send_from_directory(Config.PUBLIC_DIR, path)
    except:
        return jsonify({'error': 'File not found'}), 404

# Admin authentication routes
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    """Admin login page and authentication."""
    if request.method == 'GET':
        # Serve login page
        admin_dir = Path(__file__).parent / 'admin'
        return send_from_directory(admin_dir, 'login.html')
    
    # Handle login POST
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if authenticate(username, password):
        token = create_session('admin')
        response = jsonify({'success': True})
        response.set_cookie(
            'session_token',
            token,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            samesite='Lax',  # Changed from Strict to Lax for better compatibility
            max_age=Config.SESSION_TIMEOUT_HOURS * 3600
        )
        return response
    
    return jsonify({'success': False, 'error': 'Invalid credentials'}), 401

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
    """Serve admin dashboard JavaScript."""
    admin_dir = Path(__file__).parent / 'admin'
    return send_from_directory(admin_dir, 'dashboard.js', mimetype='application/javascript')

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
                max_workers=processing_speed
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
            
            # Run jobs outside the lock
            for job in jobs_to_run:
                try:
                    logger.info(f"Starting job {job.job_id}")
                    job.run()
                    logger.info(f"Completed job {job.job_id}")
                except Exception as e:
                    logger.error(f"Job {job.job_id} failed: {e}")
                finally:
                    save_jobs_to_disk()
            
            # Sleep before checking queue again
            import time
            time.sleep(2)
            
        except Exception as e:
            logger.error(f"Job processor error: {e}")
            import time
            time.sleep(5)
    if not election_type:
        return jsonify({'error': 'Election type is required'}), 400
    
    if not election_date:
        return jsonify({'error': 'Election date is required'}), 400
    
    # Validate file
    is_valid, error_msg = validate_file(file)
    if not is_valid:
        return jsonify({'error': error_msg}), 400
    
    # Check if another job is running
    with job_lock:
        if current_job and current_job.status == 'running':
            return jsonify({'error': 'Another job is already running'}), 409
        
        # Save file
        filepath = save_upload(file)
        
        # Create and start processing job with all metadata
        current_job = ProcessingJob(
            filepath, 
            year=year,
            county=county,
            election_type=election_type,
            election_date=election_date,
            voting_method=voting_method,
            original_filename=file.filename,
            primary_party=primary_party  # Pass primary party to processor
        )
        thread = threading.Thread(target=current_job.run)
        thread.daemon = True
        thread.start()
    
    return jsonify({
        'success': True,
        'job_id': current_job.job_id,
        'county': county,
        'year': year,
        'election_type': election_type,
        'election_date': election_date,
        'voting_method': voting_method,
        'primary_party': primary_party,
        'parsed_from_filename': {
            'year': file_info['year'],
            'county': file_info['county'],
            'election_type': file_info['election_type'],
            'party': file_info['party'],
            'is_early_voting': file_info['is_early_voting'],
            'is_cumulative': file_info['is_cumulative'],
            'description': file_info['description']
        },
        'file_info': file_info
    })

@app.route('/admin/status')
@require_auth
def get_status():
    """Get status of all processing jobs."""
    jobs_status = []
    
    with jobs_lock:
        for job_id, job in active_jobs.items():
            # Use job.cache_hits instead of geocoder stats
            cache_hits = job.cache_hits if hasattr(job, 'cache_hits') else 0
            
            # DEBUG: Log cache_hits value
            logger.info(f"[DEBUG] Job {job_id}: cache_hits={cache_hits}, processed={job.processed_records}, geocoded={job.geocoded_count}")
            
            jobs_status.append({
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
                'log_messages': job.log_messages[-20:] if hasattr(job, 'log_messages') else [],
                'errors': job.errors[:5] if hasattr(job, 'errors') else [],
                'started_at': job.started_at.isoformat() if hasattr(job, 'started_at') and job.started_at else None,
                'completed_at': job.completed_at.isoformat() if hasattr(job, 'completed_at') and job.completed_at else None
            })
    
    return jsonify({
        'jobs': jobs_status,
        'queue_length': len(job_queue),
        'active_count': sum(1 for j in jobs_status if j['status'] == 'running')
    })

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
            'completed_at': job.completed_at.isoformat() if hasattr(job, 'completed_at') and job.completed_at else None
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
                    
                    # Create a unique key for this dataset (include party for primaries)
                    dataset_key = (
                        metadata.get('county', 'Unknown'),
                        metadata.get('year', 'Unknown'),
                        metadata.get('election_type', 'Unknown'),
                        metadata.get('election_date', 'Unknown'),
                        metadata.get('voting_method', 'Unknown'),
                        metadata.get('primary_party', '')  # Include party to distinguish DEM/REP primaries
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
                        'originalFilename': metadata.get('original_filename', '')
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

@app.after_request
def set_security_headers(response):
    """Add security headers to all responses."""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://unpkg.com; "
        "font-src 'self' data: https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https: http:; "
        "connect-src 'self' https://nominatim.openstreetmap.org https://*.tile.openstreetmap.org https://*.basemaps.cartocdn.com https://cdnjs.cloudflare.com https://unpkg.com"
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

# Cleanup old uploads on startup
cleanup_old_uploads()

if __name__ == '__main__':
    logger.info("Starting WhoVoted backend server...")
    app.run(host='0.0.0.0', port=5000, debug=True)
