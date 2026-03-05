# Election Day Scraper - System Readiness Report

## Executive Summary

✅ **SYSTEM IS READY** for Election Day data import with proper Democratic/Republican party separation.

The scraper is configured to handle large-scale Election Day data with:
- Automatic party detection from ballot styles
- Separate tracking for Democratic and Republican primaries
- Robust database schema with proper indexes
- Memory-efficient batch processing
- Fallback handling for unknown party voters

---

## Party Separation - How It Works

### 1. Election Filters (Lines 42-47 in election_day_scraper.py)

```python
ELECTION_FILTERS = {
    '2026 REPUBLICAN PRIMARY': ('2026-03-03', '2026', 'primary', 'Republican'),
    '2026 DEMOCRATIC PRIMARY': ('2026-03-03', '2026', 'primary', 'Democratic'),
    '2024 REPUBLICAN PRIMARY': ('2024-03-05', '2024', 'primary', 'Republican'),
    '2024 DEMOCRATIC PRIMARY': ('2024-03-05', '2024', 'primary', 'Democratic'),
}
```

The scraper fetches BOTH Democratic and Republican primary data as separate datasets.

### 2. Party Detection Logic (Lines 217-232)

The scraper uses a **three-tier approach** to determine party:

**Tier 1: Election-level party** (from ELECTION_FILTERS)
- If scraping "2026 REPUBLICAN PRIMARY", default party is 'Republican'
- If scraping "2026 DEMOCRATIC PRIMARY", default party is 'Democratic'

**Tier 2: Ballot style detection** (overrides Tier 1)
```python
if 'DEM' in ballot_style.upper() or 'DEMOCRATIC' in ballot_style.upper():
    determined_party = 'Democratic'
elif 'REP' in ballot_style.upper() or 'REPUBLICAN' in ballot_style.upper():
    determined_party = 'Republican'
```

**Tier 3: Unknown fallback**
- If no party can be determined, marks as 'Unknown' (displayed in gray on map)

### 3. Database Storage

Each voter's party is stored in TWO places:

**voter_elections table:**
- `party_voted` column stores the party for THIS specific election
- Allows tracking party changes over time
- Used for flip detection

**voters table:**
- `current_party` column stores the most recent party
- Updated automatically after import
- Used for quick filtering

---

## Database Schema - Ready for Large Datasets

### Optimized Indexes (Added in Task 4)

```sql
-- Popup speed optimization
CREATE INDEX idx_voters_lat_lng ON voters(lat, lng);
CREATE INDEX idx_voters_address_upper ON voters(UPPER(address));
CREATE INDEX idx_ve_vuid_date_party ON voter_elections(vuid, election_date, party_voted);
CREATE INDEX idx_ve_date_party ON voter_elections(election_date, party_voted);
CREATE INDEX idx_ve_vuid_date ON voter_elections(vuid, election_date);

-- Heatmap and stats optimization
CREATE INDEX idx_ve_date_method_party ON voter_elections(election_date, voting_method, party_voted);
CREATE INDEX idx_voters_county_geocoded ON voters(county, geocoded);
CREATE INDEX idx_voters_county_vuid ON voters(county, vuid);
```

These indexes ensure fast queries even with 1M+ records.

### Batch Processing

The scraper uses `write_batch_direct()` (lines 78-139) which:
- Writes in batches to reduce database locks
- Uses `ON CONFLICT` to handle duplicates gracefully
- Preserves existing data (doesn't overwrite good data with blanks)
- Commits in transactions for data integrity

---

## Memory and Performance Considerations

### Current Server Status
- **Total RAM**: 4GB
- **Free RAM**: 2.9GB (Ollama disabled)
- **Database**: SQLite with WAL mode (concurrent reads during writes)

### Expected Election Day Data Volume
- **Estimated voters**: 1.5-2 million statewide
- **Database size increase**: ~500MB-1GB
- **Memory during import**: ~200-300MB peak
- **Import time**: 15-30 minutes (depending on API speed)

### Memory-Efficient Design

**Streaming CSV parsing** (line 207):
```python
reader = csv.DictReader(io.StringIO(csv_text))
for row in reader:
    # Process one row at a time
```

**Batch commits** (lines 78-139):
- Accumulates records in memory
- Writes in batches of 1000
- Clears memory after each batch

**No GeoJSON generation during import**:
- Import only writes to database
- GeoJSON generated on-demand when user loads map
- Saves ~1GB of memory during import

---

## What Happens During Import

### Step 1: Fetch Election List
```
GET /api-ivis-system/api/v1/getFile?type=EVR_ELECTION
```
Returns list of all available elections with IDs.

### Step 2: Download Election Day Data

**Tries statewide first:**
```
GET /api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId={id}&electionDate={date}
```

**Falls back to county-by-county if needed:**
```
GET /api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId={id}&electionDate={date}&countyId={county}
```

### Step 3: Parse and Import

For each voter in the CSV:
1. Extract VUID, name, address, precinct, ballot style
2. Determine party (using 3-tier logic above)
3. Create voter record (if new) or update (if exists)
4. Create voter_elections record with party_voted
5. Batch write to database every 1000 records

### Step 4: State Tracking

Scraper maintains state file to avoid re-importing:
```
/opt/whovoted/data/election_day_scraper_state.json
```

Safe to run multiple times - won't duplicate data.

---

## Verification After Import

### Check Total Counts

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
        WHERE election_date = '2026-03-03' AND party_voted = 'Unknown'
    ''').fetchone()[0]
    
    print(f'Total: {total:,}')
    print(f'Democratic: {dem:,}')
    print(f'Republican: {rep:,}')
    print(f'Unknown: {unknown:,}')
"
```

### Check Party Separation by County

```bash
python3 -c "
import sys
sys.path.insert(0, '/opt/whovoted/backend')
import database as db

with db.get_db() as conn:
    rows = conn.execute('''
        SELECT v.county, ve.party_voted, COUNT(*) as cnt
        FROM voter_elections ve
        JOIN voters v ON ve.vuid = v.vuid
        WHERE ve.election_date = '2026-03-03'
        GROUP BY v.county, ve.party_voted
        ORDER BY v.county, ve.party_voted
    ''').fetchall()
    
    for r in rows:
        print(f\"{r['county']}: {r['party_voted']} = {r['cnt']:,}\")
"
```

---

## Potential Issues and Solutions

### Issue 1: "Unknown" Party Voters

**Cause**: Ballot style field is empty or doesn't contain party keywords

**Impact**: Voters displayed in gray on map (still counted, just no party color)

**Solution**: This is expected and acceptable. Unknown voters are still tracked.

### Issue 2: API Rate Limiting

**Cause**: Civix API may throttle requests if scraping too fast

**Solution**: Scraper includes retry logic and delays between county requests

### Issue 3: Memory Pressure During Import

**Symptoms**: Server becomes slow, database locks

**Solution**: 
- Stop gunicorn during import: `sudo pkill -9 gunicorn`
- Run scraper: `python3 deploy/election_day_scraper.py`
- Restart gunicorn after import completes

### Issue 4: Duplicate Records

**Cause**: Running scraper multiple times

**Solution**: Database uses `ON CONFLICT` to handle duplicates gracefully. Safe to re-run.

---

## Pre-Import Checklist

✅ **Database indexes in place** (added in Task 4)
✅ **Party detection logic tested** (3-tier approach)
✅ **Batch processing configured** (1000 records per batch)
✅ **Memory available** (2.9GB free, need ~300MB)
✅ **State tracking enabled** (prevents duplicates)
✅ **Error logging configured** (`/opt/whovoted/data/election_day_scraper.log`)
✅ **Missing function fixed** (`_county_has_prior_data()` added in Task 4)

---

## Recommended Import Process

### Option 1: Quick Import (No Cache Regeneration)

```bash
cd /opt/whovoted
python3 deploy/election_day_scraper.py
```

**Time**: 15-30 minutes
**Impact**: Data imported, but caches not updated (map may show old data until refresh)

### Option 2: Full Deployment (Recommended)

```bash
cd /opt/whovoted
bash deploy/deploy_election_day_update.sh
```

**Time**: 45-60 minutes
**Impact**: 
- Imports Election Day data
- Fixes first-time voter flags
- Regenerates district cache
- Regenerates county reports
- Regenerates gazette cache
- Full system ready for users

### Option 3: Manual Step-by-Step

```bash
# Step 1: Stop gunicorn (optional, reduces memory pressure)
sudo pkill -9 gunicorn

# Step 2: Import Election Day data
cd /opt/whovoted
python3 deploy/election_day_scraper.py

# Step 3: Fix first-time voter flags
python3 deploy/fix_new_voter_flags.py

# Step 4: Regenerate caches
python3 deploy/cache_districts_only.py
python3 deploy/regenerate_county_report_cache.py
python3 deploy/generate_statewide_gazette_cache.py

# Step 5: Restart gunicorn
cd /opt/whovoted/backend
source ../venv/bin/activate
nohup gunicorn -c gunicorn_config.py -b 127.0.0.1:5000 app:app > /opt/whovoted/logs/gunicorn.log 2>&1 &
```

---

## Post-Import Verification

### 1. Check Scraper Log

```bash
tail -100 /opt/whovoted/data/election_day_scraper.log
```

Look for:
- "Successfully processed [election name]"
- "Found [X] voters"
- No error messages

### 2. Verify Database Counts

Run the verification queries above to check:
- Total voters imported
- Democratic vs Republican split
- Unknown party count (should be minimal)

### 3. Test Map Display

1. Open https://politiquera.com
2. Select "2026 Primary" from dropdown
3. Verify:
   - Blue dots for Democratic voters
   - Red dots for Republican voters
   - Gray dots for Unknown voters (if any)
   - Stats box shows correct totals

### 4. Test Voter Popups

1. Click on a voter dot
2. Verify:
   - Name, address, precinct displayed
   - Party affiliation shown
   - Flip status (if applicable)
   - First-time voter badge (if applicable)

---

## Summary

The system is **fully ready** for Election Day data import with:

1. **Robust party separation** - 3-tier detection logic ensures accurate party assignment
2. **Optimized database** - Indexes in place for fast queries with large datasets
3. **Memory-efficient processing** - Batch writes and streaming parsing
4. **Error handling** - Graceful fallbacks for unknown parties and API failures
5. **State tracking** - Safe to re-run without duplicating data
6. **Verification tools** - SQL queries to confirm data integrity

**Recommendation**: Use Option 2 (Full Deployment) for best results. This ensures all caches are updated and the system is fully ready for users.

**Estimated Time**: 45-60 minutes total (mostly automated)

**Risk Level**: Low - scraper has been tested and includes error handling

---

## Questions or Issues?

If you encounter any problems during import:

1. Check scraper log: `/opt/whovoted/data/election_day_scraper.log`
2. Check gunicorn log: `/opt/whovoted/logs/gunicorn.log`
3. Verify database integrity with verification queries above
4. Re-run scraper if needed (safe to run multiple times)

