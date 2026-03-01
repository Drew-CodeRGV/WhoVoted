#!/usr/bin/env python3
"""
EVR Scraper — Automated Texas Early Voting Turnout Data Collector

Fetches early voting data from the Texas Secretary of State's Civix platform
(goelect.txelections.civixapps.com) and imports it into the WhoVoted database.

Designed to run via cron 4x/day:
  0 6,12,18,23 * * * /opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/evr_scraper.py

API endpoints used:
  1. GET /api-ivis-system/api/v1/getFile?type=EVR_ELECTION
     → Returns base64-encoded JSON with elections list, dates, county IDs
  2. GET /api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE&electionId={id}&electionDate={date}
     → Downloads statewide CSV for a given election + date
"""

import sys
import os
import json
import csv
import io
import base64
import logging
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# Add backend to path so we can import database module (for init_db only)
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR.parent / 'backend'
sys.path.insert(0, str(BACKEND_DIR))

import database as db

# --- Configuration ---
CIVIX_BASE = 'https://goelect.txelections.civixapps.com'
EVR_ELECTION_URL = f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_ELECTION'

DATA_DIR = Path(os.getenv('EVR_DATA_DIR', '/opt/whovoted/data'))
STATE_FILE = DATA_DIR / 'evr_scraper_state.json'
LOG_FILE = DATA_DIR / 'evr_scraper.log'

# Elections we care about (add more as needed)
# Maps election name substring → (election_date for DB, election_year, election_type)
ELECTION_FILTERS = {
    '2026 REPUBLICAN PRIMARY': ('2026-03-03', '2026', 'primary', 'Republican'),
    '2026 DEMOCRATIC PRIMARY': ('2026-03-03', '2026', 'primary', 'Democratic'),
    '2024 REPUBLICAN PRIMARY': ('2024-03-05', '2024', 'primary', 'Republican'),
    '2024 DEMOCRATIC PRIMARY': ('2024-03-05', '2024', 'primary', 'Democratic'),
}

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [EVR] %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE) if LOG_FILE.parent.exists() else logging.StreamHandler(),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger('evr_scraper')

# --- Direct DB connection for scraper (avoids thread-local issues with database.py) ---
DB_PATH = Path(os.getenv('DB_PATH', '/opt/whovoted/data/whovoted.db'))
_scraper_conn = None

def get_scraper_conn():
    """Get a dedicated SQLite connection for the scraper with long timeout."""
    global _scraper_conn
    if _scraper_conn is None:
        _scraper_conn = sqlite3.connect(str(DB_PATH), timeout=60)
        _scraper_conn.execute("PRAGMA journal_mode=WAL")
        _scraper_conn.execute("PRAGMA synchronous=NORMAL")
        _scraper_conn.execute("PRAGMA cache_size=-32000")  # 32MB cache
        _scraper_conn.execute("PRAGMA busy_timeout=60000")  # 60s busy wait
    return _scraper_conn


def write_batch_direct(election_records, voter_records):
    """Write a batch of records directly using our own connection.
    
    Uses short transactions — one per batch — to minimize lock time.
    """
    conn = get_scraper_conn()
    now = datetime.now().isoformat()
    
    # Write voter_elections
    if election_records:
        params = []
        for d in election_records:
            vuid = d.get('vuid', '')
            if not vuid:
                continue
            params.append((
                vuid, d.get('election_date', ''), d.get('election_year', ''),
                d.get('election_type', ''), d.get('voting_method', ''),
                d.get('party_voted', ''), d.get('precinct', ''),
                d.get('ballot_style', ''), d.get('site', ''),
                d.get('check_in', ''), d.get('source_file', ''),
                d.get('vote_date', ''), d.get('data_source', ''),
            ))
        if params:
            conn.executemany("""
                INSERT INTO voter_elections (vuid, election_date, election_year,
                    election_type, voting_method, party_voted, precinct,
                    ballot_style, site, check_in, source_file, vote_date, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vuid, election_date, voting_method) DO UPDATE SET
                    party_voted = excluded.party_voted,
                    precinct = excluded.precinct,
                    vote_date = CASE WHEN voter_elections.vote_date IS NULL OR voter_elections.vote_date = ''
                                     THEN excluded.vote_date ELSE voter_elections.vote_date END,
                    data_source = CASE WHEN voter_elections.data_source IS NULL OR voter_elections.data_source = ''
                                       THEN excluded.data_source ELSE voter_elections.data_source END
            """, params)
    
    # Write voters
    if voter_records:
        params = []
        for d in voter_records:
            vuid = d.get('vuid', '')
            if not vuid:
                continue
            params.append((
                vuid, d.get('lastname', ''), d.get('firstname', ''),
                d.get('middlename', ''), d.get('suffix', ''),
                d.get('address', ''), d.get('city', ''), d.get('zip', ''),
                d.get('county', ''), d.get('birth_year'),
                d.get('registration_date', ''), d.get('sex', ''),
                d.get('registered_party', ''), d.get('current_party', ''),
                d.get('precinct', ''), d.get('lat'), d.get('lng'),
                1 if d.get('lat') is not None else 0,
                d.get('source', ''), now,
            ))
        if params:
            conn.executemany("""
                INSERT INTO voters (vuid, lastname, firstname, middlename, suffix,
                    address, city, zip, county, birth_year, registration_date,
                    sex, registered_party, current_party, precinct, lat, lng,
                    geocoded, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vuid) DO UPDATE SET
                    lastname = CASE WHEN excluded.lastname != '' THEN excluded.lastname ELSE voters.lastname END,
                    firstname = CASE WHEN excluded.firstname != '' THEN excluded.firstname ELSE voters.firstname END,
                    county = CASE WHEN excluded.county != '' THEN excluded.county ELSE voters.county END,
                    current_party = CASE WHEN excluded.current_party != '' THEN excluded.current_party ELSE voters.current_party END,
                    precinct = CASE WHEN excluded.precinct != '' THEN excluded.precinct ELSE voters.precinct END,
                    source = CASE WHEN excluded.source != '' THEN excluded.source ELSE voters.source END,
                    updated_at = excluded.updated_at
            """, params)
    
    conn.commit()


def load_state():
    """Load scraper state (which election+date combos we've already processed)."""
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception as e:
            log.warning(f"Could not load state file: {e}")
    return {'processed': {}, 'last_run': None}


def save_state(state):
    """Persist scraper state to disk."""
    state['last_run'] = datetime.now().isoformat()
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_elections():
    """Fetch and decode the EVR_ELECTION data from Civix API.
    
    Returns the decoded JSON object containing elections, dates, and counties.
    The API returns a base64-encoded JSON string.
    """
    log.info(f"Fetching election list from Civix API...")
    req = Request(EVR_ELECTION_URL, headers={
        'User-Agent': 'WhoVoted-EVR-Scraper/1.0',
        'Accept': 'application/json',
    })
    
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except (URLError, HTTPError) as e:
        log.error(f"Failed to fetch elections: {e}")
        return None
    
    # The API returns JSON: {"upload": "<base64-encoded-json>"}
    try:
        wrapper = json.loads(raw.decode('utf-8'))
        if isinstance(wrapper, dict) and 'upload' in wrapper:
            decoded = base64.b64decode(wrapper['upload']).decode('utf-8')
            data = json.loads(decoded)
            return data
        return wrapper
    except Exception:
        # Fallback: try direct base64 decode
        try:
            decoded = base64.b64decode(raw).decode('utf-8')
            return json.loads(decoded)
        except Exception as e:
            log.error(f"Failed to decode election data: {e}")
            return None


def download_statewide_csv(election_id, date_string):
    """Download a statewide CSV report for a given election + date.
    
    The Civix API uses getFile (not getFileByFormat) for statewide reports.
    URL: /api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE&electionId={id}&electionDate={date}
    Response: {"upload": "<base64-encoded CSV>"}
    
    date_string should be the date like "02/17/2026" (not the turnout ID).
    Returns the CSV content as a string, or None on failure.
    """
    url = f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE&electionId={election_id}&electionDate={date_string}'
    
    req = Request(url, headers={
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json',
        'Referer': f'{CIVIX_BASE}/ivis-evr-ui/evr',
    })
    
    try:
        with urlopen(req, timeout=120) as resp:
            raw = resp.read()
            data = json.loads(raw.decode('utf-8'))
            
            if not isinstance(data, dict) or 'upload' not in data:
                log.warning(f"  Unexpected response format: {str(data)[:200]}")
                return None
            
            # Decode base64 CSV content
            csv_bytes = base64.b64decode(data['upload'])
            csv_text = csv_bytes.decode('utf-8', errors='replace')
            return csv_text
            
    except (URLError, HTTPError) as e:
        log.error(f"Failed to download CSV: {e}")
        return None
    except Exception as e:
        log.error(f"Error processing download: {e}")
        return None


def process_csv(csv_text, election_date, election_year, election_type, party_voted, source_label, vote_date=''):
    """Process a statewide CSV and write records to the database.
    
    Uses the same logic as /admin/upload-state-voter-data endpoint.
    CSV columns: tx_county_name, voter_name, id_voter, voting_method, precinct
    
    Returns dict with stats.
    """
    reader = csv.reader(io.StringIO(csv_text))
    
    # Read header
    header = next(reader, None)
    if not header:
        log.warning(f"Empty CSV for {source_label}")
        return {'records': 0, 'unique': 0, 'duplicates': 0}
    
    # Normalize header
    header_lower = [h.strip().lower().replace('"', '') for h in header]
    
    # Find column indices
    county_idx = None
    name_idx = None
    vuid_idx = None
    method_idx = None
    precinct_idx = None
    
    for i, h in enumerate(header_lower):
        if h in ('tx_county_name', 'county', 'county_name'):
            county_idx = i
        elif h in ('voter_name', 'name', 'voter name'):
            name_idx = i
        elif h in ('id_voter', 'vuid', 'voter_id', 'voter id'):
            vuid_idx = i
        elif h in ('voting_method', 'method', 'voting method', 'vote_method'):
            method_idx = i
        elif h in ('tx_precinct_code', 'precinct', 'precinct_code', 'tx precinct code'):
            precinct_idx = i
    
    if vuid_idx is None:
        log.error(f"No VUID column found in CSV for {source_label}. Header: {header}")
        return {'records': 0, 'unique': 0, 'duplicates': 0}
    
    # Collect all records, dedup by VUID
    voters = {}  # vuid → record
    total_records = 0
    
    for row in reader:
        if len(row) <= vuid_idx:
            continue
        
        raw_vuid = row[vuid_idx].strip().replace('"', '')
        if not raw_vuid or not raw_vuid.isdigit():
            continue
        
        total_records += 1
        
        # Deduplicate by VUID
        if raw_vuid in voters:
            continue
        
        # Parse county name
        county = ''
        if county_idx is not None and len(row) > county_idx:
            county = row[county_idx].strip().replace('"', '').title()
        
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
        
        # Parse voting method
        voting_method = 'early-voting'
        if method_idx is not None and len(row) > method_idx:
            raw_method = row[method_idx].strip().replace('"', '').upper()
            if raw_method == 'IN-PERSON':
                voting_method = 'early-voting'
            elif raw_method in ('MAIL-IN', 'MAIL'):
                voting_method = 'mail-in'
        
        # Parse precinct
        precinct = ''
        if precinct_idx is not None and len(row) > precinct_idx:
            precinct = row[precinct_idx].strip().replace('"', '')
        
        voters[raw_vuid] = {
            'vuid': raw_vuid,
            'firstname': firstname,
            'lastname': lastname,
            'county': county,
            'party_voted': party_voted,
            'election_type': election_type,
            'voting_method': voting_method,
            'precinct': precinct,
        }
    
    unique_count = len(voters)
    duplicates = total_records - unique_count
    
    log.info(f"  {source_label}: {total_records:,} records, {unique_count:,} unique, {duplicates:,} duplicates")
    
    if unique_count == 0:
        return {'records': total_records, 'unique': 0, 'duplicates': duplicates}
    
    # Write to database in batches
    election_batch = []
    voter_batch = []
    
    for v in voters.values():
        election_batch.append({
            'vuid': v['vuid'],
            'election_date': election_date,
            'election_year': election_year,
            'election_type': v['election_type'],
            'voting_method': v['voting_method'],
            'party_voted': v['party_voted'],
            'precinct': v['precinct'],
            'ballot_style': '',
            'site': '',
            'check_in': '',
            'source_file': f'evr_scraper_{source_label}',
            'vote_date': vote_date,
            'data_source': 'tx-sos-evr',
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
            'source': 'evr-scraper',
        })
        
        if len(election_batch) >= 2000:
            write_batch_direct(election_batch, voter_batch)
            election_batch = []
            voter_batch = []
            # Give the web app time to serve reads between write batches
            time.sleep(0.5)
    
    # Flush remaining
    if election_batch:
        write_batch_direct(election_batch, voter_batch)
    
    log.info(f"  ✅ Wrote {unique_count:,} records to database")
    
    return {'records': total_records, 'unique': unique_count, 'duplicates': duplicates}


def find_matching_elections(election_data):
    """Parse the Civix election data and find elections we care about.
    
    API structure: {"elections": [{id, election_name, early_voting_dates: [{date, date_turnout_id}], ...}]}
    
    Returns list of dicts with matched elections and their available dates.
    """
    matches = []
    
    # Extract elections list
    elections = []
    if isinstance(election_data, dict) and 'elections' in election_data:
        elections = election_data['elections']
    elif isinstance(election_data, list):
        elections = election_data
    
    log.info(f"Found {len(elections)} election(s) in API response")
    
    for election in elections:
        if not isinstance(election, dict):
            continue
        
        el_name = election.get('election_name', '').strip()
        if not el_name:
            continue
        
        # Check if this election matches any of our filters
        matched_filter = None
        for filter_key, filter_vals in ELECTION_FILTERS.items():
            if filter_key.upper() in el_name.upper():
                matched_filter = (filter_key, filter_vals)
                break
        
        if not matched_filter:
            log.debug(f"  Skipping election: {el_name}")
            continue
        
        filter_key, (db_date, db_year, db_type, db_party) = matched_filter
        
        el_id = election.get('id')
        if el_id is None:
            log.warning(f"  No election ID found for: {el_name}")
            continue
        
        # Get available early voting dates
        dates = []
        for d in election.get('early_voting_dates', []):
            if isinstance(d, dict):
                date_id = d.get('date_turnout_id')
                date_label = d.get('date', str(date_id))
                if date_id is not None:
                    dates.append({'date_label': str(date_label), 'date_turnout_id': date_id})
        
        log.info(f"  ✅ Matched: {el_name} (ID={el_id}, {len(dates)} date(s))")
        
        matches.append({
            'name': el_name,
            'election_id': el_id,
            'dates': dates,
            'election_date': db_date,
            'election_year': db_year,
            'election_type': db_type,
            'party_voted': db_party,
        })
    
    return matches


def run_scraper():
    """Main scraper logic."""
    log.info("=" * 60)
    log.info("EVR Scraper starting")
    log.info("=" * 60)
    
    # Initialize database
    db.init_db()
    
    # Load state
    state = load_state()
    processed = state.get('processed', {})
    
    # Fetch election list
    election_data = fetch_elections()
    if election_data is None:
        log.error("Could not fetch election data. Aborting.")
        return False
    
    # Log raw structure for debugging (first run)
    if not processed:
        log.info(f"Raw election data type: {type(election_data).__name__}")
        if isinstance(election_data, dict):
            log.info(f"Top-level keys: {list(election_data.keys())[:20]}")
        elif isinstance(election_data, list):
            log.info(f"List length: {len(election_data)}")
            if election_data:
                first = election_data[0]
                if isinstance(first, dict):
                    log.info(f"First item keys: {list(first.keys())[:20]}")
    
    # Find elections we care about
    matches = find_matching_elections(election_data)
    
    if not matches:
        log.info("No matching elections found. Check ELECTION_FILTERS or API response format.")
        # Save raw data for debugging
        debug_file = DATA_DIR / 'evr_debug_response.json'
        try:
            debug_file.write_text(json.dumps(election_data, indent=2, default=str)[:50000])
            log.info(f"Saved debug response to {debug_file}")
        except Exception as e:
            log.warning(f"Could not save debug file: {e}")
        save_state(state)
        return True
    
    # Process each matched election
    total_new = 0
    total_updated = 0
    
    for match in matches:
        el_name = match['name']
        el_id = match['election_id']
        
        log.info(f"\nProcessing: {el_name}")
        
        for date_info in match['dates']:
            date_label = date_info['date_label']
            date_id = date_info['date_turnout_id']
            
            # Build a unique key for this election+date combo
            state_key = f"{el_id}|{date_label}"
            
            # Check if we've already processed this exact combo
            if state_key in processed:
                prev = processed[state_key]
                log.debug(f"  Already processed {date_label} ({prev.get('unique', '?')} records on {prev.get('processed_at', '?')})")
                continue
            
            log.info(f"  📥 Downloading: {el_name} — {date_label}")
            
            # Download CSV — pass the date string (e.g. "02/17/2026"), not the turnout ID
            csv_text = download_statewide_csv(el_id, date_label)
            if not csv_text:
                log.warning(f"  ⚠️ Empty or failed download for {date_label}")
                continue
            
            # Quick sanity check
            line_count = csv_text.count('\n')
            log.info(f"  Downloaded {len(csv_text):,} bytes, ~{line_count:,} lines")
            
            if line_count < 2:
                log.warning(f"  ⚠️ CSV too small ({line_count} lines), skipping")
                continue
            
            # Process and write to DB
            # Convert date_label (MM/DD/YYYY) to ISO format (YYYY-MM-DD) for vote_date
            vote_date_iso = ''
            try:
                parts = date_label.split('/')
                if len(parts) == 3:
                    vote_date_iso = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
            except Exception:
                vote_date_iso = date_label
            
            source_label = f"{el_name}_{date_label}".replace(' ', '_').replace('/', '-')
            stats = process_csv(
                csv_text,
                election_date=match['election_date'],
                election_year=match['election_year'],
                election_type=match['election_type'],
                party_voted=match['party_voted'],
                source_label=source_label,
                vote_date=vote_date_iso,
            )
            
            # Record in state
            processed[state_key] = {
                'election_name': el_name,
                'date_label': date_label,
                'records': stats['records'],
                'unique': stats['unique'],
                'duplicates': stats['duplicates'],
                'processed_at': datetime.now().isoformat(),
            }
            
            total_new += stats['unique']
            
            # Save state after each date so we don't re-process if killed
            state['processed'] = processed
            save_state(state)
            
            # Be polite — small delay between downloads
            time.sleep(2)
        
    # Final state save
    state['processed'] = processed
    save_state(state)
    
    log.info(f"\n{'=' * 60}")
    log.info(f"EVR Scraper complete: {total_new:,} new records imported")
    log.info(f"{'=' * 60}")
    
    return True


if __name__ == '__main__':
    try:
        success = run_scraper()
        # Close our direct connection
        if _scraper_conn:
            _scraper_conn.close()
        
        # Trigger performance optimization after successful scrape
        if success:
            log.info("Triggering post-scrape optimization...")
            import subprocess
            try:
                result = subprocess.run(
                    ['/opt/whovoted/venv/bin/python3', '/opt/whovoted/deploy/optimize_performance.py'],
                    capture_output=True, text=True, timeout=600
                )
                if result.returncode == 0:
                    log.info("Post-scrape optimization completed successfully")
                else:
                    log.warning(f"Optimization failed: {result.stderr}")
            except Exception as e:
                log.warning(f"Could not run optimization: {e}")
        
        sys.exit(0 if success else 1)
    except Exception as e:
        log.exception(f"Scraper crashed: {e}")
        if _scraper_conn:
            _scraper_conn.close()
        sys.exit(1)
