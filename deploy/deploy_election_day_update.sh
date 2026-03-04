#!/bin/bash
# Deploy election day data and fix first-time voter logic

set -e  # Exit on error

echo "================================================================================"
echo "ELECTION DAY DATA IMPORT & FIRST-TIME VOTER FIX"
echo "================================================================================"
echo ""

cd /opt/whovoted

# Step 1: Fix first-time voter flags
echo "Step 1: Recalculating first-time voter flags..."
echo "--------------------------------------------------------------------------------"
python3 deploy/fix_new_voter_flags.py
echo ""

# Step 2: Download election day data
echo "Step 2: Downloading election day voting data..."
echo "--------------------------------------------------------------------------------"
python3 deploy/election_day_scraper.py
echo ""

# Step 3: Regenerate district cache
echo "Step 3: Regenerating district cache (includes TX-15)..."
echo "--------------------------------------------------------------------------------"
python3 deploy/cache_districts_only.py
echo ""

# Step 4: Regenerate county reports
echo "Step 4: Regenerating county reports..."
echo "--------------------------------------------------------------------------------"
python3 deploy/regenerate_county_report_cache.py
echo ""

# Step 5: Regenerate gazette cache
echo "Step 5: Regenerating gazette cache..."
echo "--------------------------------------------------------------------------------"
python3 deploy/generate_statewide_gazette_cache.py
echo ""

# Step 6: Verify results
echo "Step 6: Verifying results..."
echo "--------------------------------------------------------------------------------"
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
    
    new_total = conn.execute('''
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND is_new_voter = 1
    ''').fetchone()[0]
    
    early = conn.execute('''
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND voting_method = 'early-voting'
    ''').fetchone()[0]
    
    electionday = conn.execute('''
        SELECT COUNT(*) FROM voter_elections
        WHERE election_date = '2026-03-03' AND voting_method = 'election-day'
    ''').fetchone()[0]
    
    print(f'2026-03-03 Primary:')
    print(f'  Total voters: {total:,}')
    print(f'  Early voting: {early:,}')
    print(f'  Election day: {electionday:,}')
    print(f'  First-time voters: {new_total:,} ({new_total/total*100:.1f}%)')
    print()
    
    # TX-15 stats
    tx15 = conn.execute('''
        SELECT COUNT(*) as total,
               SUM(CASE WHEN is_new_voter = 1 THEN 1 ELSE 0 END) as new_voters,
               SUM(CASE WHEN voting_method = 'early-voting' THEN 1 ELSE 0 END) as early,
               SUM(CASE WHEN voting_method = 'election-day' THEN 1 ELSE 0 END) as electionday
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
          AND v.county IN ('Hidalgo', 'Cameron', 'Willacy', 'Brooks')
    ''').fetchone()
    
    print(f'TX-15 District:')
    print(f'  Total voters: {tx15[0]:,}')
    print(f'  Early voting: {tx15[2]:,}')
    print(f'  Election day: {tx15[3]:,}')
    print(f'  First-time voters: {tx15[1]:,} ({tx15[1]/tx15[0]*100:.1f}%)')
"

echo ""
echo "================================================================================"
echo "DEPLOYMENT COMPLETE"
echo "================================================================================"
echo ""
echo "Next steps:"
echo "  1. Check website: https://politiquera.com/"
echo "  2. Verify TX-15 numbers look reasonable"
echo "  3. Check county reports"
echo ""
