# Data Sync Issue - March 2, 2026

## Problem
Database totals don't match official Hidalgo County numbers:
- **Official (from PDF):** 49,664 D, 13,217 R, 62,881 total
- **Database:** 49,459 D, 13,238 R, 62,697 total  
- **Difference:** -205 D, +21 R, -184 total (0.3% off)

## Root Cause
The automated EVR scraper pulls from the Texas SOS Civix API, which updates slower than Hidalgo County's own website. The county publishes PDFs daily, but the API lags by 12-24 hours.

## Solution Options

### Option 1: Manual Upload (Fastest - 5 minutes)
1. Go to Hidalgo County Elections website
2. Download latest roster files:
   - `EV DEM Roster March 3, 2026 (Cumulative).xlsx`
   - `EV REP Roster March 3, 2026 (Cumulative).xlsx`
3. Go to https://politiquera.com/admin
4. Upload both files
5. System will automatically process and update database

### Option 2: Wait for API Update (Automatic - 12-24 hours)
The cron job runs 4x daily (6am, 12pm, 6pm, 11pm). Once the Civix API updates with the latest data, it will automatically sync.

### Option 3: Force Re-scrape (If API has new data)
```bash
ssh -i "WhoVoted/deploy/whovoted-key.pem" ubuntu@54.164.71.129
cd /opt/whovoted
# Backup state file
cp data/evr_scraper_state.json data/evr_scraper_state.json.backup
# Clear state to force re-download
echo '{"processed": {}, "last_run": null}' > data/evr_scraper_state.json
# Run scraper
/opt/whovoted/venv/bin/python3 deploy/evr_scraper.py
```

## Additional Issues Found

### 1. Duplicate Votes
2 VUIDs voted twice (both early-voting AND mail-in):
- VUID: 1053174475 (Democratic, Democratic)
- VUID: 1054489617 (Democratic, Democratic)

**Fix:** Update all queries to use `COUNT(DISTINCT vuid)` instead of `COUNT(*)` to avoid double-counting.

### 2. Missing County Data
32 voter records have no county assigned, which could cause them to be excluded from county-specific queries.

## Recommended Actions
1. **Immediate:** Manually upload latest roster files (Option 1)
2. **Short-term:** Fix duplicate counting in all API endpoints
3. **Long-term:** Add direct scraper for Hidalgo County website to supplement Civix API

## Files to Check
- Latest roster location: https://www.hidalgocounty.us/Elections.aspx
- Or contact Hidalgo County Elections: (956) 318-2570
