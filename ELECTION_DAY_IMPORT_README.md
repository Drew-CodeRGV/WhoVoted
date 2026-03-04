# Election Day Data Import - Instructions

## What This Does

Imports election day voting data from the Texas Secretary of State's Civix platform for ALL counties in the 2026 primary election (both Democratic and Republican).

## Key Features

1. **No Geocoding**: Data is imported without triggering geocoding (saves time and API costs)
2. **Unknown Party Handling**: Voters whose party cannot be determined are marked as "Unknown" and displayed in gray on the map
3. **All Counties**: Scrapes data for all 254 Texas counties
4. **Both Parties**: Imports both Democratic and Republican primary data

## Files Created

- `deploy/election_day_scraper.py` - Main scraper script
- `deploy/import_election_day_only.sh` - Import script (no geocoding, no cache regen)
- `deploy/deploy_election_day_update.sh` - Full deployment (includes first-time voter fix and cache regen)
- `deploy/fix_new_voter_flags.py` - Recalculates first-time voter flags with new logic

## Map Color Scheme

After import, voters will be displayed with these colors:

- **Blue (#1E90FF)**: Democratic voters
- **Red (#DC143C)**: Republican voters
- **Gray (#808080)**: Unknown party (election day voters where party couldn't be determined)
- **Purple (#6A1B9A)**: Party flippers (R→D)
- **Maroon (#8B0000)**: Party flippers (D→R)
- **Light Gray (#A0A0A0)**: Registered but didn't vote

## Quick Start (Import Only - No Geocoding)

```bash
# On the server
cd /opt/whovoted
bash deploy/import_election_day_only.sh
```

This will:
1. Download election day data from Civix API
2. Import into database
3. Show summary statistics
4. **NOT** trigger geocoding
5. **NOT** regenerate caches

## Full Deployment (With First-Time Voter Fix)

```bash
# On the server
cd /opt/whovoted
bash deploy/deploy_election_day_update.sh
```

This will:
1. Fix first-time voter logic (recalculate all flags)
2. Download and import election day data
3. Regenerate district cache (TX-15)
4. Regenerate county reports
5. Regenerate gazette cache
6. Show verification statistics

## Manual Steps (If Needed)

### Step 1: Import Election Day Data Only
```bash
python3 deploy/election_day_scraper.py
```

### Step 2: Fix First-Time Voter Flags
```bash
python3 deploy/fix_new_voter_flags.py
```

### Step 3: Regenerate Caches
```bash
# District cache (includes TX-15)
python3 deploy/cache_districts_only.py

# County reports
python3 deploy/regenerate_county_report_cache.py

# Gazette cache
python3 deploy/generate_statewide_gazette_cache.py
```

## Verification

After import, check the numbers:

```bash
python3 -c "
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
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
    
    print(f'Total: {total:,}')
    print(f'Early: {early:,}')
    print(f'Election Day: {electionday:,}')
"
```

## Expected Results

- **Total voters**: ~1.5-2 million (statewide)
- **Early voting**: ~40-50% of total
- **Election day**: ~50-60% of total
- **Unknown party**: Should be minimal (most voters have party from ballot style)

## Troubleshooting

### Issue: "No election day data found"
- Check if the Civix API is accessible
- Verify the election ID and date are correct
- Try running with verbose logging

### Issue: "Too many unknown party voters"
- This is expected if ballot style data is missing
- Unknown voters are still counted and displayed (just in gray)

### Issue: "First-time voter numbers still wrong"
- Run `python3 deploy/fix_new_voter_flags.py` again
- Check that you have prior election data (2022, 2024)
- Verify the logic in `FINAL_FIRST_TIME_LOGIC.md`

## API Endpoints Used

The scraper uses these Civix API endpoints:

1. **Election List**: 
   ```
   GET /api-ivis-system/api/v1/getFile?type=EVR_ELECTION
   ```

2. **Election Day Data** (tries multiple patterns):
   ```
   GET /api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId={id}&electionDate={date}
   GET /api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId={id}&electionDate={date}&countyId={county}
   ```

## State Files

The scraper maintains state to avoid re-importing:

- `/opt/whovoted/data/election_day_scraper_state.json` - Tracks which elections have been processed
- `/opt/whovoted/data/election_day_scraper.log` - Detailed log of scraper activity

## Notes

- The scraper is idempotent - safe to run multiple times
- Existing voter records are updated, not duplicated
- Election day data is marked with `voting_method = 'election-day'`
- Data source is marked as `data_source = 'civix_election_day'`
