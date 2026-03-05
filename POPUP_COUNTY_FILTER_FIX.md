# Voter Popup County Filter Fix

## Issue
When selecting a specific county (e.g., Brooks County), voter markers would appear on the map, but clicking on them would not load voter details in the popup. The popup would show "Loading voter details..." indefinitely or show "No voter details found".

## Root Cause
The `/api/voters/at` endpoint was not filtering by county. When a user selected a specific county:
1. The map would load only markers for that county
2. But when clicking a marker, the popup query would search ALL counties
3. This could return no results or wrong results, especially for counties with limited data

## Solution
Added county filtering to the voter popup loading system:

### Frontend Changes (`public/data.js`)
- Updated `_lazyLoadPopup()` function to pass county parameter to API
- Uses `window.selectedCountyFilter` or `dataset.selectedCounties` to determine which county(ies) to query
- Only sends county parameter when a specific county is selected (not "all")

### Backend Changes (`backend/app.py`)
- Updated `/api/voters/at` endpoint to accept optional `county` parameter
- Parses comma-separated list of counties
- Passes counties list to database function

### Database Changes (`backend/database.py`)
- Updated `get_voters_at_location()` function signature to accept `counties` parameter
- Added county filtering to both SQL queries:
  - Step 1: Finding address near coordinates
  - Step 2: Finding all voters at that address
- Uses `IN` clause with placeholders for multiple counties

## Testing
1. Select a specific county (e.g., Brooks County)
2. Zoom in to see voter markers
3. Click on a marker
4. Popup should now load voter details correctly

## Deployment
```bash
cd /opt/whovoted
git pull origin main
rm -rf backend/__pycache__
sudo pkill -9 gunicorn
source venv/bin/activate
PYTHONDONTWRITEBYTECODE=1 nohup gunicorn -c gunicorn_config.py -b 127.0.0.1:5000 backend.app:app > logs/gunicorn.log 2>&1 &
```

## Files Modified
- `public/data.js` - Added county parameter to API call
- `backend/app.py` - Updated endpoint to accept county parameter
- `backend/database.py` - Added county filtering to SQL queries

## Status
✅ Deployed to production (March 5, 2026)
