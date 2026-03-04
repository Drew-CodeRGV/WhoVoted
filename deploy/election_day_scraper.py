#!/usr/bin/env python3
"""
Election Day Scraper — Texas Election Day Turnout Data Collector

Fetches election day voting data from the Texas Secretary of State's Civix platform
(goelect.txelections.civixapps.com) and imports it into the WhoVoted database.

Similar to evr_scraper.py but for election day data instead of early voting.

API endpoints:
  1. GET /api-ivis-system/api/v1/getFile?type=EVR_ELECTION
     → Returns base64-encoded JSON with elections list
  2. GET /api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId={id}&electionDate={date}
     → Downloads statewide CSV for election day voting
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

# Add backend to path
SCRIPT_DIR = Path(__file__).parent.resolve()
BACKEND_DIR = SCRIPT_DIR.parent / 'backend'
sys.path.insert(0, str(BACKEND_DIR))

import database as db

# --- Configuration ---
CIVIX_BASE = 'https://goelect.txelections.civixapps.com'
EVR_ELECTION_URL = f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_ELECTION'

DATA_DIR = Path(os.getenv('EVR_DATA_DIR', '/opt/whovoted/data'))
STATE_FILE = DATA_DIR / 'election_day_scraper_state.json'
LOG_FILE = DATA_DIR / 'election_day_scraper.log'

# Elections we care about
ELECTION_FILTERS = {
    '2026 REPUBLICAN PRIMARY': ('2026-03-03', '2026', 'primary', 'Republican'),
    '2026 DEMOCRATIC PRIMARY': ('2026-03-03', '2026', 'primary', 'Democratic'),
    '2024 REPUBLICAN PRIMARY': ('2024-03-05', '2024', 'primary', 'Republican'),
    '2024 DEMOCRATIC PRIMARY': ('2024-03-05', '2024', 'primary', 'Democratic'),
}

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [ELECTIONDAY] %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE) if LOG_FILE.parent.exists() else logging.StreamHandler(),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger('election_day_scraper')

# --- Direct DB connection ---
DB_PATH = Path(os.getenv('DB_PATH', '/opt/whovoted/data/whovoted.db'))
_scraper_conn = None

def get_scraper_conn():
    """Get a dedicated SQLite connection for the scraper."""
    global _scraper_conn
    if _scraper_conn is None:
        _scraper_conn = sqlite3.connect(str(DB_PATH), timeout=60)
        _scraper_conn.execute("PRAGMA journal_mode=WAL")
        _scraper_conn.execute("PRAGMA synchronous=NORMAL")
        _scraper_conn.execute("PRAGMA cache_size=-32000")
        _scraper_conn.execute("PRAGMA busy_timeout=60000")
    return _scraper_conn


def write_batch_direct(election_records, voter_records):
    """Write a batch of records directly using our own connection."""
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
            log.info(f"  Inserted/updated {len(params)} voter_elections records")
    
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
            log.info(f"  Inserted/updated {len(params)} voters records")
    
    conn.commit()


def load_state():
    """Load scraper state."""
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
    """Fetch and decode the EVR_ELECTION data from Civix API."""
    log.info(f"Fetching election list from Civix API...")
    req = Request(EVR_ELECTION_URL, headers={
        'User-Agent': 'WhoVoted-ElectionDay-Scraper/1.0',
        'Accept': 'application/json',
    })
    
    try:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
    except (URLError, HTTPError) as e:
        log.error(f"Failed to fetch elections: {e}")
        return None
    
    try:
        wrapper = json.loads(raw.decode('utf-8'))
        if isinstance(wrapper, dict) and 'upload' in wrapper:
            decoded = base64.b64decode(wrapper['upload']).decode('utf-8')
            data = json.loads(decoded)
            return data
        return wrapper
    except Exception:
        try:
            decoded = base64.b64decode(raw).decode('utf-8')
            return json.loads(decoded)
        except Exception as e:
            log.error(f"Failed to decode election data: {e}")
            return None


def download_election_day_csv(election_id, election_date_str, county_id=None):
    """Download election day CSV for a given election.
    
    URL pattern based on the UI link you provided:
    /api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId={id}&electionDate={date}
    
    If county_id is provided, downloads county-specific data.
    Otherwise downloads statewide data.
    
    Returns the CSV content as a string, or None on failure.
    """
    # Try multiple URL patterns
    if county_id:
        urls_to_try = [
            f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId={election_id}&electionDate={election_date_str}&countyId={county_id}',
            f'{CIVIX_BASE}/api-ivis-system/api/v1/getFileByFormat?type=ELECTION_DAY&electionId={election_id}&electionDate={election_date_str}&countyId={county_id}&format=csv',
        ]
    else:
        urls_to_try = [
            f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId={election_id}&electionDate={election_date_str}',
            f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EV&electionId={election_id}&electionDate={election_date_str}',
            f'{CIVIX_BASE}/api-ivis-system/api/v1/getFileByFormat?type=ELECTION_DAY&electionId={election_id}&electionDate={election_date_str}&format=csv',
        ]
    
    for url in urls_to_try:
        log.info(f"  Trying: {url}")
        req = Request(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Referer': f'{CIVIX_BASE}/ivis-evr-ui/official-election-day-voting-information',
        })
        
        try:
            with urlopen(req, timeout=120) as resp:
                raw = resp.read()
                data = json.loads(raw.decode('utf-8'))
                
                if not isinstance(data, dict) or 'upload' not in data:
                    log.warning(f"  Unexpected response format")
                    continue
                
                # Decode base64 CSV content
                csv_bytes = base64.b64decode(data['upload'])
                csv_text = csv_bytes.decode('utf-8', errors='replace')
                log.info(f"  ✓ Successfully downloaded election day data")
                return csv_text
                
        except (URLError, HTTPError) as e:
            log.warning(f"  Failed: {e}")
            continue
        except Exception as e:
            log.warning(f"  Error: {e}")
            continue
    
    log.error(f"  All URL patterns failed for election {election_id}")
    return None


def parse_csv_to_records(csv_text, election_date, election_year, election_type, party):
    """Parse CSV text into voter and election records.
    
    Expected CSV columns (similar to EVR format):
    VUID, Last Name, First Name, Middle Name, Suffix, Address, City, Zip,
    County, Birth Year, Registration Date, Sex, Precinct, Ballot Style, etc.
    
    If party cannot be determined from the data, marks as 'Unknown'.
    """
    election_records = []
    voter_records = []
    
    reader = csv.DictReader(io.StringIO(csv_text))
    
    for row in reader:
        vuid = row.get('VUID', '').strip()
        if not vuid:
            continue
        
        # Try to determine party from ballot style or other fields
        determined_party = party  # Default to the election party
        ballot_style = row.get('Ballot Style', '').strip()
        
        # If ballot style indicates party, use that
        if ballot_style:
            if 'DEM' in ballot_style.upper() or 'DEMOCRATIC' in ballot_style.upper():
                determined_party = 'Democratic'
            elif 'REP' in ballot_style.upper() or 'REPUBLICAN' in ballot_style.upper():
                determined_party = 'Republican'
            elif not party or party == 'Unknown':
                # Can't determine party - mark as Unknown
                determined_party = 'Unknown'
        
        # Parse birth year
        birth_year = None
        dob = row.get('Date of Birth', '') or row.get('DOB', '')
        if dob:
            try:
                birth_year = int(dob.split('/')[-1]) if '/' in dob else int(dob[:4])
            except:
                pass
        
        # Voter record
        voter_records.append({
            'vuid': vuid,
            'lastname': row.get('Last Name', '').strip(),
            'firstname': row.get('First Name', '').strip(),
            'middlename': row.get('Middle Name', '').strip(),
            'suffix': row.get('Suffix', '').strip(),
            'address': row.get('Residence Address', '').strip() or row.get('Address', '').strip(),
            'city': row.get('City', '').strip(),
            'zip': row.get('Zip Code', '').strip() or row.get('Zip', '').strip(),
            'county': row.get('County', '').strip(),
            'birth_year': birth_year,
            'registration_date': row.get('Registration Date', '').strip(),
            'sex': row.get('Sex', '').strip(),
            'registered_party': '',
            'current_party': determined_party,
            'precinct': row.get('Precinct', '').strip(),
            'lat': None,
            'lng': None,
            'source': 'civix_election_day',
        })
        
        # Election record
        election_records.append({
            'vuid': vuid,
            'election_date': election_date,
            'election_year': election_year,
            'election_type': election_type,
            'voting_method': 'election-day',
            'party_voted': determined_party,
            'precinct': row.get('Precinct', '').strip(),
            'ballot_style': ballot_style,
            'site': row.get('Polling Place', '').strip() or row.get('Site', '').strip(),
            'check_in': row.get('Check In Time', '').strip() or row.get('Time', '').strip(),
            'source_file': f'election_day_{election_date}_{determined_party}.csv',
            'vote_date': election_date,
            'data_source': 'civix_election_day',
        })
    
    return election_records, voter_records


def find_matching_elections(election_data):
    """Parse the Civix election data and find elections we care about."""
    if not election_data or 'elections' not in election_data:
        log.error("Invalid election data structure")
        return []
    
    matches = []
    for election in election_data['elections']:
        election_name = election.get('election_name', '').upper()
        election_id = election.get('id')
        
        # Check if this election matches our filters
        for filter_name, (db_date, year, etype, party) in ELECTION_FILTERS.items():
            if filter_name.upper() in election_name:
                # For election day, we just need the election date (not individual early voting dates)
                matches.append({
                    'election_id': election_id,
                    'election_name': election.get('election_name'),
                    'election_date': db_date,
                    'election_year': year,
                    'election_type': etype,
                    'party': party,
                    'date_string': db_date.replace('-', '/').lstrip('0').replace('/0', '/'),  # Format for API: "3/3/2026"
                })
                break
    
    return matches


def main():
    """Main scraper logic."""
    log.info("=" * 80)
    log.info("ELECTION DAY SCRAPER STARTED")
    log.info("=" * 80)
    
    # Load state
    state = load_state()
    processed = state.get('processed', {})
    
    # Fetch elections list
    election_data = fetch_elections()
    if not election_data:
        log.error("Failed to fetch election data. Exiting.")
        return 1
    
    # Find matching elections
    matches = find_matching_elections(election_data)
    if not matches:
        log.warning("No matching elections found")
        return 0
    
    log.info(f"Found {len(matches)} matching elections")
    
    # Process each election
    for match in matches:
        election_id = match['election_id']
        election_name = match['election_name']
        election_date = match['election_date']
        date_string = match['date_string']
        party = match['party']
        
        # Check if already processed
        state_key = f"{election_id}_{election_date}_electionday"
        if state_key in processed:
            log.info(f"Skipping {election_name} (already processed)")
            continue
        
        log.info(f"\nProcessing: {election_name}")
        log.info(f"  Election ID: {election_id}")
        log.info(f"  Date: {election_date}")
        log.info(f"  Party: {party}")
        
        # Download CSV - try statewide first, then by county if needed
        csv_text = download_election_day_csv(election_id, date_string)
        
        # If statewide fails, try getting all counties individually
        if not csv_text and election_data.get('counties'):
            log.info(f"  Statewide download failed, trying county-by-county...")
            all_csv_parts = []
            for county in election_data['counties']:
                county_id = county.get('id')
                county_name = county.get('county_name', 'Unknown')
                log.info(f"    Downloading {county_name} (ID: {county_id})...")
                county_csv = download_election_day_csv(election_id, date_string, county_id)
                if county_csv:
                    # Skip header for subsequent counties
                    if all_csv_parts:
                        county_csv = '\n'.join(county_csv.split('\n')[1:])
                    all_csv_parts.append(county_csv)
            
            if all_csv_parts:
                csv_text = '\n'.join(all_csv_parts)
                log.info(f"  ✓ Combined data from {len(all_csv_parts)} counties")
        
        if not csv_text:
            log.error(f"  Failed to download election day data")
            continue
        
        # Parse CSV
        log.info(f"  Parsing CSV...")
        election_records, voter_records = parse_csv_to_records(
            csv_text, election_date, match['election_year'], 
            match['election_type'], party
        )
        
        log.info(f"  Found {len(election_records)} voters")
        
        if election_records:
            # Write to database
            log.info(f"  Writing to database...")
            write_batch_direct(election_records, voter_records)
            
            # Mark as processed
            processed[state_key] = {
                'timestamp': datetime.now().isoformat(),
                'voters': len(election_records),
            }
            save_state(state)
            
            log.info(f"  ✓ Successfully processed {election_name}")
        else:
            log.warning(f"  No records found in CSV")
    
    log.info("\n" + "=" * 80)
    log.info("ELECTION DAY SCRAPER COMPLETED")
    log.info("=" * 80)
    
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        log.info("\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        sys.exit(1)
