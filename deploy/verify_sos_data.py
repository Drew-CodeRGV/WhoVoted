#!/usr/bin/env python3
"""Download latest data from Texas SOS and compare with database."""
import sqlite3
import requests
import csv
from io import StringIO
from collections import defaultdict

DB_PATH = '/opt/whovoted/data/whovoted.db'

# Texas SOS Early Voting Roster URL for Hidalgo County 2026 Primary
# Format: https://teamrv-mvp.sos.texas.gov/MVP/mvp.do
SOS_URL = "https://teamrv-mvp.sos.texas.gov/MVP/back/download.do"

def download_sos_data():
    """Download the latest early voting roster from Texas SOS."""
    print("Downloading latest data from Texas Secretary of State...")
    print("URL: https://teamrv-mvp.sos.texas.gov/MVP/mvp.do")
    print("\nNote: This requires manual download. Please:")
    print("1. Go to https://teamrv-mvp.sos.texas.gov/MVP/mvp.do")
    print("2. Select County: Hidalgo")
    print("3. Select Election: 2026 Primary")
    print("4. Download the CSV file")
    print("5. Save it as /tmp/hidalgo_2026_sos.csv")
    print("\nWaiting for file...")
    
    # Check if file exists
    import os
    csv_path = '/tmp/hidalgo_2026_sos.csv'
    if not os.path.exists(csv_path):
        print(f"\n❌ File not found: {csv_path}")
        print("Please download manually and save to that location.")
        return None
    
    print(f"✓ Found file: {csv_path}")
    return csv_path

def analyze_sos_data(csv_path):
    """Analyze the SOS CSV data."""
    print("\nAnalyzing SOS data...")
    
    sos_vuids = set()
    sos_dem = 0
    sos_rep = 0
    sos_by_method = defaultdict(lambda: {'dem': 0, 'rep': 0, 'total': 0})
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            vuid = row.get('VUID', '').strip()
            party = row.get('Party', '').strip()
            method = row.get('Voting Method', '').strip().lower()
            
            if not vuid:
                continue
            
            sos_vuids.add(vuid)
            
            if party == 'DEM':
                sos_dem += 1
                sos_by_method[method]['dem'] += 1
            elif party == 'REP':
                sos_rep += 1
                sos_by_method[method]['rep'] += 1
            
            sos_by_method[method]['total'] += 1
    
    print(f"\nSOS Data Summary:")
    print(f"  Total records: {len(sos_vuids):,}")
    print(f"  Democratic: {sos_dem:,}")
    print(f"  Republican: {sos_rep:,}")
    print(f"  Total: {sos_dem + sos_rep:,}")
    
    print(f"\nBy voting method:")
    for method, counts in sorted(sos_by_method.items()):
        print(f"  {method:20s}: {counts['total']:>6,} ({counts['dem']:>6,} D, {counts['rep']:>6,} R)")
    
    return sos_vuids, sos_dem, sos_rep, sos_by_method

def compare_with_database(sos_vuids, sos_dem, sos_rep):
    """Compare SOS data with database."""
    print("\n" + "="*70)
    print("COMPARING SOS DATA WITH DATABASE")
    print("="*70)
    
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    
    # Get database VUIDs
    db_rows = conn.execute("""
        SELECT ve.vuid, ve.party_voted, ve.voting_method
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE v.county = 'Hidalgo'
          AND ve.election_date = '2026-03-03'
    """).fetchall()
    
    db_vuids = set()
    db_dem = 0
    db_rep = 0
    db_by_vuid = defaultdict(list)
    
    for row in db_rows:
        vuid = str(row['vuid'])
        db_vuids.add(vuid)
        db_by_vuid[vuid].append({
            'party': row['party_voted'],
            'method': row['voting_method']
        })
        
        if row['party_voted'] == 'Democratic':
            db_dem += 1
        elif row['party_voted'] == 'Republican':
            db_rep += 1
    
    # Find unique VUIDs in database
    db_unique_vuids = set(db_by_vuid.keys())
    
    print(f"\nDatabase Summary:")
    print(f"  Total records: {len(db_rows):,}")
    print(f"  Unique VUIDs: {len(db_unique_vuids):,}")
    print(f"  Democratic: {db_dem:,}")
    print(f"  Republican: {db_rep:,}")
    
    # Find differences
    missing_in_db = sos_vuids - db_unique_vuids
    extra_in_db = db_unique_vuids - sos_vuids
    
    print(f"\n" + "="*70)
    print("DISCREPANCIES")
    print("="*70)
    
    print(f"\nVUIDs in SOS but NOT in database: {len(missing_in_db):,}")
    if missing_in_db and len(missing_in_db) <= 20:
        print("  Sample VUIDs:")
        for vuid in list(missing_in_db)[:20]:
            print(f"    {vuid}")
    
    print(f"\nVUIDs in database but NOT in SOS: {len(extra_in_db):,}")
    if extra_in_db and len(extra_in_db) <= 20:
        print("  Sample VUIDs:")
        for vuid in list(extra_in_db)[:20]:
            print(f"    {vuid}")
    
    # Check duplicates in database
    duplicates = [vuid for vuid, votes in db_by_vuid.items() if len(votes) > 1]
    if duplicates:
        print(f"\nDuplicate VUIDs in database: {len(duplicates)}")
        for vuid in duplicates:
            votes = db_by_vuid[vuid]
            print(f"  {vuid}: {len(votes)} votes")
            for v in votes:
                print(f"    - {v['party']} via {v['method']}")
    
    print(f"\n" + "="*70)
    print("TOTALS COMPARISON")
    print("="*70)
    print(f"\n{'Source':<20} {'Democratic':>12} {'Republican':>12} {'Total':>12}")
    print("-" * 70)
    print(f"{'SOS (Official)':<20} {sos_dem:>12,} {sos_rep:>12,} {sos_dem+sos_rep:>12,}")
    print(f"{'Database (Raw)':<20} {db_dem:>12,} {db_rep:>12,} {db_dem+db_rep:>12,}")
    print(f"{'Database (Unique)':<20} {len([v for v in db_by_vuid.values() if any(x['party']=='Democratic' for x in v)]):>12,} {len([v for v in db_by_vuid.values() if any(x['party']=='Republican' for x in v)]):>12,} {len(db_unique_vuids):>12,}")
    
    conn.close()

if __name__ == '__main__':
    print("="*70)
    print("TEXAS SOS DATA VERIFICATION")
    print("="*70)
    
    csv_path = download_sos_data()
    
    if csv_path:
        sos_vuids, sos_dem, sos_rep, sos_by_method = analyze_sos_data(csv_path)
        compare_with_database(sos_vuids, sos_dem, sos_rep)
    else:
        print("\n⚠️  Cannot proceed without SOS data file.")
        print("\nAlternative: Check the admin upload logs for the last import:")
        print("  - When was the last successful import?")
        print("  - Were there any errors or warnings?")
        print("  - How many records were imported?")
