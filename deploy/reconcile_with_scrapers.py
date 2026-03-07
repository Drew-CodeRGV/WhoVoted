#!/usr/bin/env python3
"""
Reconcile database with what's available from EVR and Election Day scrapers
Strategy:
1. Check what data we have vs what scrapers can provide
2. Identify source of 505 extra D15 votes
3. Fix by keeping only scraper data
"""
import sqlite3
import json
import csv
import io
import base64
import zipfile
from urllib.request import urlopen, Request

DB_PATH = '/opt/whovoted/data/whovoted.db'
CIVIX_BASE = 'https://goelect.txelections.civixapps.com'

def fetch_evr_count(election_id, election_date):
    """Get count of records available from EVR scraper"""
    date_parts = election_date.split('-')
    date_formatted = f'{date_parts[1]}/{date_parts[2]}/{date_parts[0]}'
    
    url = f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE&electionId={election_id}&electionDate={date_formatted}'
    
    req = Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    
    try:
        with urlopen(req, timeout=300) as response:
            data = response.read()
        
        json_data = json.loads(data.decode('utf-8'))
        file_bytes = base64.b64decode(json_data['upload'])
        
        if file_bytes[:2] == b'PK':
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                csv_files = [name for name in zf.namelist() if name.endswith('.csv')]
                if csv_files:
                    csv_text = zf.read(csv_files[0]).decode('utf-8', errors='replace')
                    csv_text = csv_text.replace('\x00', '')
                    reader = csv.DictReader(io.StringIO(csv_text))
                    return sum(1 for _ in reader)
        return 0
    except Exception as e:
        print(f"  Error fetching EVR: {e}")
        return 0

def fetch_election_day_count(election_id, election_date):
    """Get count of records available from Election Day scraper"""
    date_parts = election_date.split('-')
    date_formatted = f'{date_parts[1]}/{date_parts[2]}/{date_parts[0]}'
    
    url = f'{CIVIX_BASE}/api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE_ELECTIONDAY&electionId={election_id}&electionDate={date_formatted}'
    
    req = Request(url)
    req.add_header('User-Agent', 'Mozilla/5.0')
    req.add_header('Accept', 'application/json')
    
    try:
        with urlopen(req, timeout=300) as response:
            data = response.read()
        
        json_data = json.loads(data.decode('utf-8'))
        file_bytes = base64.b64decode(json_data['upload'])
        
        if file_bytes[:2] == b'PK':
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                csv_files = [name for name in zf.namelist() if name.endswith('.csv')]
                if csv_files:
                    csv_text = zf.read(csv_files[0]).decode('utf-8', errors='replace')
                    csv_text = csv_text.replace('\x00', '')
                    reader = csv.DictReader(io.StringIO(csv_text))
                    return sum(1 for _ in reader)
        return 0
    except Exception as e:
        print(f"  Error fetching Election Day: {e}")
        return 0

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    print("="*80)
    print("RECONCILING WITH SCRAPER DATA")
    print("="*80)
    
    # Check what we have in database
    print("\n[DATABASE] Current 2026-03-03 data:")
    cursor.execute("""
        SELECT 
            party_voted,
            data_source,
            COUNT(DISTINCT vuid) as unique_voters,
            COUNT(*) as total_records
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        AND party_voted IN ('Democratic', 'Republican')
        GROUP BY party_voted, data_source
        ORDER BY party_voted, unique_voters DESC
    """)
    
    db_totals = {}
    for party, source, unique, total in cursor.fetchall():
        print(f"  {party:<12} {source or 'NULL':<25} {unique:>10,} voters  {total:>10,} records")
        if party not in db_totals:
            db_totals[party] = {'total': 0, 'by_source': {}}
        db_totals[party]['by_source'][source or 'NULL'] = unique
    
    # Get unique totals per party
    cursor.execute("""
        SELECT 
            party_voted,
            COUNT(DISTINCT vuid) as unique_voters
        FROM voter_elections
        WHERE election_date = '2026-03-03'
        AND party_voted IN ('Democratic', 'Republican')
        GROUP BY party_voted
    """)
    for party, unique in cursor.fetchall():
        db_totals[party]['total'] = unique
        print(f"\n  {party} TOTAL: {unique:,} unique voters")
    
    # Check scraper availability
    print("\n" + "-"*80)
    print("[SCRAPERS] Checking available data...")
    
    elections = [
        {'name': 'Democratic', 'id': '53814', 'date': '2026-03-03'},
        {'name': 'Republican', 'id': '53813', 'date': '2026-03-03'}
    ]
    
    scraper_totals = {}
    for election in elections:
        print(f"\n{election['name']} Primary:")
        print(f"  Fetching EVR data...")
        evr_count = fetch_evr_count(election['id'], election['date'])
        print(f"    EVR records available: {evr_count:,}")
        
        print(f"  Fetching Election Day data...")
        ed_count = fetch_election_day_count(election['id'], election['date'])
        print(f"    Election Day records available: {ed_count:,}")
        
        scraper_totals[election['name']] = {
            'evr': evr_count,
            'election_day': ed_count,
            'total': evr_count + ed_count
        }
    
    # Compare
    print("\n" + "="*80)
    print("COMPARISON")
    print("="*80)
    
    for party in ['Democratic', 'Republican']:
        print(f"\n{party}:")
        db_total = db_totals.get(party, {}).get('total', 0)
        scraper_total = scraper_totals.get(party, {}).get('total', 0)
        
        print(f"  Database: {db_total:,} voters")
        print(f"  Scrapers: {scraper_total:,} records available")
        print(f"  Difference: {db_total - scraper_total:,}")
        
        if db_total != scraper_total:
            print(f"  ⚠ MISMATCH - Need to reconcile")
        else:
            print(f"  ✓ Match")
    
    conn.close()
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)

if __name__ == '__main__':
    main()
