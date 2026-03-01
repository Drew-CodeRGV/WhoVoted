"""Import election participation history from map_data files into the voter_elections table.

For each map_data file, reads the metadata to determine the election (date, type, party,
voting method) and records each VUID's participation. This creates the immutable election
record that drives party affiliation and flip detection.

The voter_elections table has UNIQUE(vuid, election_date, voting_method) so re-running
this script is safe — it will upsert without duplicating.
"""
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, '/opt/whovoted/backend')
from config import Config
import database as db

def run():
    db.init_db()
    conn = db.get_connection()
    data_dir = Config.PUBLIC_DIR / 'data'
    
    total_records = 0
    total_files = 0
    
    for meta_file in sorted(data_dir.glob('metadata_*.json')):
        try:
            with open(meta_file, 'r') as f:
                meta = json.load(f)
            
            if not meta:
                print(f"  {meta_file.name}: empty metadata, skipping")
                continue
            
            # Skip cumulative files
            if meta.get('is_cumulative'):
                continue
            
            # Get election info from metadata
            election_date = meta.get('election_date', '')
            election_year = meta.get('year', '')
            election_type = meta.get('election_type', '')
            voting_method = meta.get('voting_method', '')
            primary_party = meta.get('primary_party', '')
            county = meta.get('county', '')
            source_file = meta.get('original_filename', meta_file.name)
            
            # Determine party from primary_party or election_type
            party_voted = ''
            if primary_party:
                if 'dem' in primary_party.lower():
                    party_voted = 'Democratic'
                elif 'rep' in primary_party.lower():
                    party_voted = 'Republican'
            
            # Find corresponding map_data file
            map_data_name = 'map_data_' + meta_file.name[len('metadata_'):]
            map_data_path = data_dir / map_data_name
            
            if not map_data_path.exists():
                print(f"  {meta_file.name}: no map_data file, skipping")
                continue
            
            with open(map_data_path, 'r') as f:
                geojson = json.load(f)
            
            features = geojson.get('features', [])
            batch = []
            file_count = 0
            
            for feature in features:
                props = feature.get('properties', {})
                
                vuid = str(props.get('vuid', '')).strip()
                if not vuid or vuid == 'nan':
                    continue
                if vuid.endswith('.0'):
                    vuid = vuid[:-2]
                if not (len(vuid) == 10 and vuid.isdigit()):
                    continue
                
                # Get precinct and other data from the feature
                precinct = str(props.get('precinct', '')).strip()
                ballot_style = str(props.get('ballot_style', '')).strip()
                site = str(props.get('site', '')).strip()
                check_in = str(props.get('check_in', '')).strip()
                
                # If no party_voted from metadata, try to get from feature properties
                voter_party = party_voted
                if not voter_party:
                    pac = str(props.get('party_affiliation_current', '')).strip()
                    if pac:
                        voter_party = pac
                
                batch.append({
                    'vuid': vuid,
                    'election_date': election_date,
                    'election_year': election_year,
                    'election_type': election_type,
                    'voting_method': voting_method,
                    'party_voted': voter_party,
                    'precinct': precinct,
                    'ballot_style': ballot_style,
                    'site': site,
                    'check_in': check_in,
                    'source_file': source_file
                })
                file_count += 1
                
                if len(batch) >= 500:
                    db.record_elections_batch(batch)
                    batch = []
            
            if batch:
                db.record_elections_batch(batch)
            
            conn.commit()
            total_records += file_count
            total_files += 1
            
            vm_label = 'EV' if 'early' in voting_method.lower() else 'ED'
            print(f"  {meta_file.name}: {file_count:,} records "
                  f"({election_date} {election_type} {party_voted} {vm_label})")
            
        except Exception as e:
            print(f"  {meta_file.name}: ERROR {e}")
    
    print(f"\nImported {total_records:,} election participation records from {total_files} files")
    
    # Now update current_party for all voters based on most recent election
    print("\nUpdating current_party from election history...")
    updated = db.update_all_current_parties()
    print(f"Updated current_party for {updated:,} voters")
    
    # Detect flips and flip-flops
    print("\nAnalyzing party switches...")
    
    # Get all unique election dates
    dates = conn.execute(
        "SELECT DISTINCT election_date FROM voter_elections ORDER BY election_date"
    ).fetchall()
    election_dates = [d[0] for d in dates]
    print(f"Election dates in DB: {election_dates}")
    
    # For each voter with 2+ elections, check for flips
    voters_with_history = conn.execute("""
        SELECT vuid, GROUP_CONCAT(party_voted || '|' || election_date, ',') as history
        FROM (
            SELECT DISTINCT vuid, party_voted, election_date 
            FROM voter_elections 
            WHERE party_voted != '' AND party_voted IS NOT NULL
            ORDER BY election_date
        )
        GROUP BY vuid
        HAVING COUNT(DISTINCT election_date) >= 2
    """).fetchall()
    
    flips = 0
    flip_flops = 0
    
    for vuid, history_str in voters_with_history:
        entries = history_str.split(',')
        parties_by_date = []
        for entry in entries:
            parts = entry.split('|')
            if len(parts) == 2:
                party, date = parts
                parties_by_date.append((date, party))
        
        # Sort by date and deduplicate (same date = same election, keep one)
        parties_by_date.sort()
        seen_dates = set()
        unique_parties = []
        for date, party in parties_by_date:
            if date not in seen_dates:
                seen_dates.add(date)
                unique_parties.append(party)
        
        if len(unique_parties) < 2:
            continue
        
        # Check for switches
        switches = 0
        for i in range(1, len(unique_parties)):
            if unique_parties[i] != unique_parties[i-1]:
                switches += 1
        
        if switches >= 2:
            flip_flops += 1
        elif switches == 1:
            flips += 1
    
    print(f"\nParty switch analysis:")
    print(f"  Voters with 2+ elections: {len(voters_with_history):,}")
    print(f"  Single flips (A→B):       {flips:,}")
    print(f"  Flip-flops (A→B→A):       {flip_flops:,}")
    print(f"  Total switchers:          {flips + flip_flops:,}")
    
    # Final stats
    total_elections = conn.execute("SELECT COUNT(*) FROM voter_elections").fetchone()[0]
    unique_voters_voted = conn.execute("SELECT COUNT(DISTINCT vuid) FROM voter_elections").fetchone()[0]
    print(f"\nFinal DB stats:")
    print(f"  Total election records: {total_elections:,}")
    print(f"  Unique voters who voted: {unique_voters_voted:,}")
    
    # Party breakdown from current_party
    party_rows = conn.execute("""
        SELECT current_party, COUNT(*) as cnt FROM voters 
        WHERE current_party != '' AND current_party IS NOT NULL
        GROUP BY current_party ORDER BY cnt DESC
    """).fetchall()
    print(f"  Current party breakdown:")
    for party, count in party_rows:
        print(f"    {party}: {count:,}")

if __name__ == '__main__':
    run()
