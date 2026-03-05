# Election Day Data Import Status

## Current Status: DATA NOT PUBLISHED YET

As of March 4, 2026, the Texas Secretary of State has not yet published the election day data to the Civix platform. Both the API and web UI show no election day data available.

All Civix API endpoints return HTTP 500 errors, and the web UI at https://goelect.txelections.civixapps.com/ivis-evr-ui/evr does not show election day turnout data yet.

## When Data Becomes Available

The state typically publishes election day data within a few days to weeks after the election. Once published, you have two options:

### Option 1: Automatic Scraper (Recommended)

The scraper will automatically detect and import the data once the API is working:

```bash
# Test if API is working
/opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/check_election_day_api.py

# Run scraper when API is available
/opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/election_day_scraper.py
```

## Tested API Endpoints (All Failing)

All of these return HTTP 500:
- `/api-ivis-system/api/v1/getFile?type=ELECTION_DAY&electionId={id}&electionDate={date}`
- `/api-ivis-system/api/v1/getFile?type=ELECTION_DAY_STATEWIDE&electionId={id}`
- `/api-ivis-system/api/v1/getFile?type=OFFICIAL_ELECTION_DAY&electionId={id}`
- `/api-ivis-system/api/v1/getFile?type=ED&electionId={id}`
- `/api-ivis-system/api/v1/getFile?type=ELECTION_DAY_ROSTER&electionId={id}`

## System Readiness

The system is fully prepared to handle election day data:

✅ Database schema supports 'election-day' voting_method
✅ Map displays gray markers for 'Unknown' party voters
✅ Gazette toggle supports election day filtering
✅ API endpoints filter by voting_method
✅ Scraper ready (waiting for API)
✅ Upload interface accepts election day files

### Option 2: Manual Download

If the data appears in the web UI before the API works:

1. Go to https://goelect.txelections.civixapps.com/ivis-evr-ui/evr
2. Select "2026 DEMOCRATIC PRIMARY ELECTION" from the dropdown
3. Look for "Unofficial Election Day Turnout by County" section
4. Download the CSV file
5. Repeat for "2026 REPUBLICAN PRIMARY ELECTION"
6. Upload via admin dashboard at https://politiquera.com/admin/dashboard.html

## Next Steps

1. **Monitor**: Check the Civix platform periodically for when data is published
2. **Run Scraper**: Execute the scraper once API is available
3. **Regenerate Cache**: Run gazette cache generation after import
4. **Test Gazette**: Verify all three toggle views work correctly

## Monitoring Command

Set up a cron job to check daily:
```bash
# Add to crontab
0 9 * * * /opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/check_election_day_api.py && /opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/election_day_scraper.py
```
