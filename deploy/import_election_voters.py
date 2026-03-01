"""Import VUIDs from map_data election files that are NOT in the voter registry DB.

These are voters who voted in elections but aren't in the registration file.
We pull their VUID, name, address, coordinates, and party from the GeoJSON files
and insert them into the voter DB so we have complete records.
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
    
    # Get all VUIDs already in the DB
    print("Loading existing VUIDs from DB...")
    existing_vuids = set()
    cursor = conn.execute("SELECT vuid FROM voters")
    for row in cursor:
        existing_vuids.add(row[0])
    print(f"  Existing VUIDs in DB: {len(existing_vuids):,}")
    
    # Collect VUIDs from map_data files that are NOT in the DB
    # Keep the richest data (most fields) for each VUID
    new_voters = {}  # vuid -> record dict
    
    for f in sorted(data_dir.glob('map_data_*.json')):
        try:
            # Parse metadata from filename for election info
            meta_name = 'metadata_' + f.name[len('map_data_'):]
            meta_path = data_dir / meta_name
            meta = {}
            if meta_path.exists():
                with open(meta_path, 'r') as mf:
                    meta = json.load(mf) or {}
            
            with open(f, 'r') as fh:
                geojson = json.load(fh)
            
            count = 0
            for feature in geojson.get('features', []):
                props = feature.get('properties', {})
                geom = feature.get('geometry')
                if not geom:
                    continue
                coords = geom.get('coordinates', [])
                
                vuid = str(props.get('vuid', '')).strip()
                if not vuid:
                    vuid = str(props.get('cert', '')).strip()
                if not vuid:
                    continue
                
                # Skip if already in DB
                if vuid in existing_vuids:
                    continue
                
                lat = float(coords[1]) if len(coords) >= 2 else None
                lng = float(coords[0]) if len(coords) >= 2 else None
                
                # Extract name
                lastname = str(props.get('lastname', '')).strip()
                firstname = str(props.get('firstname', '')).strip()
                middlename = str(props.get('middlename', '')).strip()
                suffix = str(props.get('suffix', '')).strip()
                
                # Extract address
                address = str(props.get('address', '')).strip()
                if not address:
                    address = str(props.get('original_address', '')).strip()
                
                # Extract party
                party = str(props.get('party_affiliation_current', '')).strip()
                if not party:
                    party = meta.get('primary_party', '')
                    if party:
                        party = 'Democratic' if 'dem' in party.lower() else 'Republican' if 'rep' in party.lower() else party
                
                # Build record — keep the one with the most data
                record = {
                    'vuid': vuid,
                    'lastname': lastname,
                    'firstname': firstname,
                    'middlename': middlename,
                    'suffix': suffix,
                    'address': address,
                    'city': '',
                    'zip': '',
                    'county': meta.get('county', 'Hidalgo'),
                    'birth_year': None,
                    'registration_date': '',
                    'sex': '',
                    'registered_party': '',
                    'current_party': party,
                    'precinct': str(props.get('precinct', '')).strip(),
                    'lat': lat,
                    'lng': lng,
                    'source': 'election_file'
                }
                
                # Keep the record with the most non-empty fields
                if vuid not in new_voters:
                    new_voters[vuid] = record
                    count += 1
                else:
                    # Update if this record has more data
                    existing = new_voters[vuid]
                    for key in ['lastname', 'firstname', 'address', 'current_party', 'precinct']:
                        if record[key] and not existing[key]:
                            existing[key] = record[key]
                    if record['lat'] and not existing['lat']:
                        existing['lat'] = record['lat']
                        existing['lng'] = record['lng']
            
            print(f"  {f.name}: {count} new VUIDs")
        except Exception as e:
            print(f"  {f.name}: ERROR {e}")
    
    print(f"\nTotal new VUIDs to import: {len(new_voters):,}")
    
    # Count how many have coordinates
    with_coords = sum(1 for v in new_voters.values() if v.get('lat'))
    without_coords = len(new_voters) - with_coords
    print(f"  With coordinates: {with_coords:,}")
    print(f"  Without coordinates: {without_coords:,}")
    
    # Insert into DB in batches
    batch = []
    batch_size = 500
    inserted = 0
    
    for vuid, record in new_voters.items():
        batch.append(record)
        if len(batch) >= batch_size:
            db.upsert_voters_batch(batch)
            inserted += len(batch)
            batch = []
            if inserted % 5000 == 0:
                print(f"  Inserted: {inserted:,}")
    
    if batch:
        db.upsert_voters_batch(batch)
        inserted += len(batch)
    
    print(f"\nInserted {inserted:,} new voter records from election files")
    
    # Print final stats
    total = conn.execute("SELECT COUNT(*) FROM voters").fetchone()[0]
    geocoded = conn.execute("SELECT COUNT(*) FROM voters WHERE geocoded = 1").fetchone()[0]
    pct = geocoded / total * 100 if total > 0 else 0
    print(f"\nFinal DB: {total:,} total voters, {geocoded:,} geocoded ({pct:.1f}%)")


if __name__ == '__main__':
    run()
