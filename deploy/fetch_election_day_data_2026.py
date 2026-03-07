#!/usr/bin/env python3
"""
Fetch 2026 Primary Election Day data from Texas SOS IVIS system
Standalone script - no backend dependencies needed
"""

import json
import csv
import io
import base64
import sqlite3
import gzip
import zipfile
from urllib.request import urlopen, Request
from datetime import datetime
from pathlib import Path

# Configuration
CIVIX_BASE = 'https://goelect.txelections.civixapps.com'
EVR_ELECTION_URL = f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_ELECTION'
DB_PATH = '/opt/whovoted/data/whovoted.db'

# Elections to fetch
ELECTIONS_TO_FETCH = [
    {
        'name': '2026 DEMOCRATIC PRIMARY ELECTION',
        'election_id': '53814',
        'election_date': '2026-03-03',
        'party': 'Democratic',
        'url_name': '2026%20DEMOCRATIC%20PRIMARY%20ELECTION'
    },
    {
        'name': '2026 REPUBLICAN PRIMARY ELECTION',
        'election_id': '53813',
        'election_date': '2026-03-03',
        'party': 'Republican',
        'url_name': '2026%20REPUBLICAN%20PRIMARY%20ELECTION'
    }
]

def fetch_election_day_csv(election_id, election_date, election_name):
    """Fetch election day CSV from IVIS API"""
    # Format date as MM/DD/YYYY for API
    date_parts = election_date.split('-')
    date_formatted = f'{date_parts[1]}/{date_parts[2]}/{date_parts[0]}'
    
    # Use EVR_STATEWIDE_ELECTIONDAY endpoint
    url = f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE_ELECTIONDAY&electionId={election_id}&electionDate={date_formatted}'
    
    print(f"  Fetching from: {url}")
    
    req = Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    req.add_header('Accept', 'application/json')
    req.add_header('Referer', f'{CIVIX_BASE}/ivis-evr-ui/official-election-day-voting-information')
    
    try:
        with urlopen(req, timeout=300) as response:
            data = response.read()
            
        # Parse JSON response
        json_data = json.loads(data.decode('utf-8'))
        
        if not isinstance(json_data, dict) or 'upload' not in json_data:
            print(f"  Error: Unexpected response format")
            return None
        
        # Decode base64 content
        file_bytes = base64.b64decode(json_data['upload'])
        
        # Check if it's a ZIP file (starts with PK)
        if file_bytes[:2] == b'PK':
            print(f"  ✓ Received ZIP file, extracting...")
            # Extract CSV from ZIP
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                # Get the first CSV file in the ZIP
                csv_files = [name for name in zf.namelist() if name.endswith('.csv')]
                if not csv_files:
                    print(f"  Error: No CSV file found in ZIP")
                    return None
                
                print(f"  ✓ Extracting {csv_files[0]}...")
                csv_text = zf.read(csv_files[0]).decode('utf-8', errors='replace')
                return csv_text
        else:
            # Not a ZIP, treat as plain CSV
            csv_text = file_bytes.decode('utf-8', errors='replace')
            return csv_text
        
    except Exception as e:
        print(f"  Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return None

def parse_csv_data(csv_text):
    """Parse CSV text into records"""
    # Remove NUL characters that might be in the data
    csv_text = csv_text.replace('\x00', '')
    
    # Try to parse as CSV
    try:
        reader = csv.DictReader(io.StringIO(csv_text))
        records = []
        
        for row in reader:
            records.append(row)
        
        return records
    except Exception as e:
        print(f"  Error parsing CSV: {e}")
        print(f"  First 500 chars: {csv_text[:500]}")
        return []

def import_to_database(records, election_info):
    """Import records into database"""
    # Use WAL mode and longer timeout for concurrent access
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.execute('PRAGMA journal_mode=WAL')
    conn.execute('PRAGMA busy_timeout=30000')
    cursor = conn.cursor()
    
    source_file = f"election_day_{election_info['party']}_{election_info['election_date']}"
    inserted = 0
    updated = 0
    empty_vuid = 0
    errors = 0
    
    print(f"  Sample record: {records[0] if records else 'No records'}")
    
    batch_size = 1000
    
    for i, record in enumerate(records):
        # The field is called 'id_voter' in this format, not 'VUID'
        vuid = record.get('id_voter', '').strip() or record.get('VUID', '').strip()
        if not vuid:
            empty_vuid += 1
            continue
        
        # Extract fields - note different field names
        county = record.get('tx_county_name', '') or record.get('County', '')
        precinct = record.get('tx_precinct_code', '') or record.get('Precinct', '')
        ballot_style = record.get('Ballot Style', '')
        check_in = record.get('Check In', '')
        voting_method_raw = record.get('voting_method', 'ELECTION-DAY').upper()
        
        try:
            # Determine voting method FIRST
            if 'MAIL' in voting_method_raw:
                voting_method = 'mail-in'
            elif 'EARLY' in voting_method_raw:
                voting_method = 'early-voting'
            else:
                voting_method = 'election-day'
            
            # Check if record exists
            cursor.execute("""
                SELECT id FROM voter_elections
                WHERE vuid = ? AND election_date = ? AND voting_method = ?
            """, (vuid, election_info['election_date'], voting_method))
            
            existing = cursor.fetchone()
            
            # Use INSERT OR REPLACE to handle duplicates
            # This will update existing records or insert new ones
            cursor.execute("""
                INSERT INTO voter_elections 
                (vuid, election_date, election_year, election_type, voting_method, 
                 party_voted, precinct, ballot_style, check_in, source_file, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vuid, election_date, voting_method) 
                DO UPDATE SET
                    precinct = excluded.precinct,
                    ballot_style = excluded.ballot_style,
                    check_in = excluded.check_in,
                    source_file = excluded.source_file,
                    data_source = excluded.data_source
            """, (
                vuid,
                election_info['election_date'],
                '2026',
                'primary',
                voting_method,
                election_info['party'],
                precinct,
                ballot_style,
                check_in,
                source_file,
                'tx-sos-election-day'
            ))
            
            if existing:
                updated += 1
            else:
                inserted += 1
            
            # Commit in batches to reduce lock time
            if (i + 1) % batch_size == 0:
                conn.commit()
                print(f"  Progress: {i+1:,}/{len(records):,} records processed...")
                
        except Exception as e:
            if 'locked' in str(e).lower():
                # Retry once on lock error
                import time
                time.sleep(0.5)
                try:
                    cursor.execute("""
                        INSERT INTO voter_elections 
                        (vuid, election_date, election_year, election_type, voting_method, 
                         party_voted, precinct, ballot_style, check_in, source_file, data_source)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ON CONFLICT(vuid, election_date, voting_method) 
                        DO UPDATE SET
                            precinct = excluded.precinct,
                            ballot_style = excluded.ballot_style,
                            check_in = excluded.check_in,
                            source_file = excluded.source_file,
                            data_source = excluded.data_source
                    """, (
                        vuid,
                        election_info['election_date'],
                        '2026',
                        'primary',
                        voting_method,
                        election_info['party'],
                        precinct,
                        ballot_style,
                        check_in,
                        source_file,
                        'tx-sos-election-day'
                    ))
                    if existing:
                        updated += 1
                    else:
                        inserted += 1
                except:
                    errors += 1
            else:
                errors += 1
    
    conn.commit()
    conn.close()
    
    if empty_vuid > 0:
        print(f"  ⚠ Skipped {empty_vuid:,} records with empty VUID")
    
    return inserted, updated, errors
    
    print(f"  Sample record: {records[0] if records else 'No records'}")
    
    for record in records:
        # The field is called 'id_voter' in this format, not 'VUID'
        vuid = record.get('id_voter', '').strip() or record.get('VUID', '').strip()
        if not vuid:
            empty_vuid += 1
            continue
        
        # Extract fields - note different field names
        county = record.get('tx_county_name', '') or record.get('County', '')
        precinct = record.get('tx_precinct_code', '') or record.get('Precinct', '')
        ballot_style = record.get('Ballot Style', '')
        check_in = record.get('Check In', '')
        voting_method_raw = record.get('voting_method', 'ELECTION-DAY').upper()
        
        try:
            # Determine voting method FIRST
            if 'MAIL' in voting_method_raw:
                voting_method = 'mail-in'
            elif 'EARLY' in voting_method_raw:
                voting_method = 'early-voting'
            else:
                voting_method = 'election-day'
            
            # Use INSERT OR REPLACE to handle duplicates
            # This will update existing records or insert new ones
            cursor.execute("""
                INSERT INTO voter_elections 
                (vuid, election_date, election_year, election_type, voting_method, 
                 party_voted, precinct, ballot_style, check_in, source_file, data_source)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(vuid, election_date, voting_method) 
                DO UPDATE SET
                    precinct = excluded.precinct,
                    ballot_style = excluded.ballot_style,
                    check_in = excluded.check_in,
                    source_file = excluded.source_file,
                    data_source = excluded.data_source
            """, (
                vuid,
                election_info['election_date'],
                '2026',
                'primary',
                voting_method,
                election_info['party'],
                precinct,
                ballot_style,
                check_in,
                source_file,
                'tx-sos-election-day'
            ))
            
            imported += 1
                
        except Exception as e:
            print(f"  Error importing VUID {vuid}: {e}")
            skipped += 1
    
    conn.commit()
    conn.close()
    
    if empty_vuid > 0:
        print(f"  ⚠ Skipped {empty_vuid:,} records with empty VUID")
    
    return imported, skipped

def main():
    print("="*80)
    print("FETCHING 2026 PRIMARY ELECTION DAY DATA")
    print("="*80)
    
    for election in ELECTIONS_TO_FETCH:
        print(f"\n{election['name']}")
        print("-" * 80)
        
        # Fetch CSV data
        csv_data = fetch_election_day_csv(election['election_id'], election['election_date'], election['url_name'])
        
        if not csv_data:
            print(f"  ✗ Failed to fetch data")
            continue
        
        # Parse CSV
        records = parse_csv_data(csv_data)
        print(f"  ✓ Fetched {len(records):,} records")
        
        # Import to database
        inserted, updated, errors = import_to_database(records, election)
        print(f"  ✓ Inserted: {inserted:,} new records")
        print(f"  ✓ Updated: {updated:,} existing records")
        if errors > 0:
            print(f"  ⚠ Errors: {errors:,} records failed")
    
    print("\n" + "="*80)
    print("VERIFYING D15 DEMOCRATIC VOTES")
    print("="*80)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT COUNT(DISTINCT ve.vuid)
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.congressional_district = '15'
        AND ve.election_date = '2026-03-03'
        AND ve.party_voted = 'Democratic'
    """)
    
    total = cursor.fetchone()[0]
    print(f"\nD15 Democratic votes after import: {total:,}")
    print(f"Expected: 54,573")
    print(f"Difference: {54573 - total:,}")
    
    conn.close()
    
    print("\n" + "="*80)
    print("✓ COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
