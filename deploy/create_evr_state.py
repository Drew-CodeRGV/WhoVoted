#!/usr/bin/env python3
"""Create EVR scraper state file from existing DB data so it doesn't re-process."""
import json
import sqlite3
from datetime import datetime

db_path = '/opt/whovoted/data/whovoted.db'
state_file = '/opt/whovoted/data/evr_scraper_state.json'

conn = sqlite3.connect(db_path, timeout=30)

# Get all EVR records grouped by vote_date and party
rows = conn.execute('''
    SELECT vote_date, party_voted, COUNT(*) as cnt
    FROM voter_elections
    WHERE data_source = 'tx-sos-evr'
    GROUP BY vote_date, party_voted
    ORDER BY vote_date, party_voted
''').fetchall()

conn.close()

# Build state file
# The scraper uses state_key = f"{el_id}|{date_label}" where date_label is MM/DD/YYYY
# Election IDs: 53813 = Republican, 53814 = Democratic
processed = {}

for vote_date, party, count in rows:
    # Convert YYYY-MM-DD to MM/DD/YYYY
    parts = vote_date.split('-')
    if len(parts) == 3:
        date_label = f"{parts[1]}/{parts[2]}/{parts[0]}"
    else:
        date_label = vote_date
    
    el_id = 53813 if party == 'Republican' else 53814
    state_key = f"{el_id}|{date_label}"
    
    processed[state_key] = {
        'election_name': f'2026 {party.upper()} PRIMARY ELECTION',
        'date_label': date_label,
        'records': count,
        'unique': count,
        'duplicates': 0,
        'processed_at': datetime.now().isoformat(),
    }
    print(f"  {state_key}: {count:,} records")

state = {'processed': processed}

with open(state_file, 'w') as f:
    json.dump(state, f, indent=2)

print(f"\nWrote state file with {len(processed)} entries to {state_file}")
