#!/bin/bash
# Import election day data ONLY - no geocoding, no cache regeneration

set -e

echo "================================================================================"
echo "ELECTION DAY DATA IMPORT (No Geocoding)"
echo "================================================================================"
echo ""

cd /opt/whovoted

echo "Downloading and importing election day voting data..."
echo "This will import data for ALL counties (Democratic and Republican primaries)"
echo "Voters with unknown party will be marked as 'Unknown'"
echo ""
echo "Starting import..."
python3 deploy/election_day_scraper.py

echo ""
echo "================================================================================"
echo "IMPORT COMPLETE"
echo "================================================================================"
echo ""
echo "Summary:"
python3 -c "
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    # Overall stats
    total = conn.execute('''
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03'
    ''').fetchone()[0]
    
    early = conn.execute('''
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND voting_method = 'early-voting'
    ''').fetchone()[0]
    
    electionday = conn.execute('''
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND voting_method = 'election-day'
    ''').fetchone()[0]
    
    dem = conn.execute('''
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND party_voted = 'Democratic'
    ''').fetchone()[0]
    
    rep = conn.execute('''
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND party_voted = 'Republican'
    ''').fetchone()[0]
    
    unknown = conn.execute('''
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND (party_voted = 'Unknown' OR party_voted = '' OR party_voted IS NULL)
    ''').fetchone()[0]
    
    print(f'2026-03-03 Primary:')
    print(f'  Total voters: {total:,}')
    print(f'  Early voting: {early:,}')
    print(f'  Election day: {electionday:,}')
    print(f'')
    print(f'By party:')
    print(f'  Democratic: {dem:,}')
    print(f'  Republican: {rep:,}')
    print(f'  Unknown: {unknown:,}')
"

echo ""
echo "Next steps:"
echo "  1. Fix first-time voter logic: bash deploy/deploy_election_day_update.sh"
echo "  2. Or run individual steps as needed"
echo ""
