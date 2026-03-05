# Popup Loading Fix - March 5, 2026

## Issues Fixed

### 1. Popup Loading Returns 0 Voters (RESOLVED)
**Problem**: When clicking markers on the map, popups showed "0 voters" or "No voter details found" even in areas with many voters.

**Root Cause**: The frontend was passing `voting_method=combined` to the backend API `/api/voters/at`. The database only has specific voting methods ("early-voting", "election-day", "mail-in") - "combined" is a frontend-only concept for displaying aggregated data.

**Solution**: Modified `_lazyLoadPopup()` and `preloadViewportVoterDetails()` functions in `public/data.js` to NOT pass the `voting_method` parameter when the dataset is "combined".

**Files Changed**:
- `public/data.js` (lines 1385-1388, 368-373)
- `public/index.html` (version bump to `data.js?v=20260305d`)

**Commit**: 75657b0 - "Fix popup loading: don't pass voting_method=combined to backend"

### 2. Duplicate Voting History Entries (RESOLVED)
**Problem**: Voter popups showed duplicate "ED" (Election Day) entries in voting history.

**Investigation**: 
- Checked database for duplicate 2026 entries - found NONE
- Database is clean - each voter has only one entry per election
- Issue was a display bug, not a data integrity problem

**Solution**: Added deduplication logic in `fetchVoterHistory()` function to group history by election year, keeping only one entry per year (preferring election-day over early-voting since it's chronologically later).

**Files Changed**:
- `public/data.js` (lines 2383-2395)
- `public/index.html` (version bump to `data.js?v=20260305e`)

**Commit**: 683beee - "Fix duplicate voting history entries - deduplicate by year"

## Verification Scripts Created

### check_duplicate_2026.py
Checks for voters with multiple entries for the 2026 election.
- Result: 0 duplicates found
- Confirms database integrity is intact

### check_voter_history_sample.py
Displays the voter_elections table schema and shows a sample voter's complete voting history.
- Confirms each voter has only one entry per election
- Shows proper data structure

## Deployment

All fixes deployed to production server at politiquera.com:
```bash
cd /opt/whovoted
git pull origin main
# No gunicorn restart needed - frontend-only changes
```

## User Action Required

Users must do a hard refresh to clear browser cache:
- Windows: `Ctrl + Shift + R` or `Ctrl + F5`
- Mac: `Cmd + Shift + R`

This loads the latest JavaScript version (`data.js?v=20260305e`) with all fixes.

## Outstanding Issue

### Geocoding Accuracy
Some voter addresses are geocoded to incorrect locations (e.g., markers appearing in undeveloped areas far from the actual address). This is a separate issue from popup loading and requires investigation of the geocoding process.

**Next Steps**:
1. Identify which geocoding service/method is being used
2. Check geocoding quality metrics
3. Consider re-geocoding addresses with low confidence scores
4. Implement validation to flag obviously incorrect coordinates

## Technical Details

### Frontend Cache Management
The popup system uses a browser-side cache (`_voterDetailCache`) to store voter details:
- Keyed by rounded coordinates (lat,lng to 5 decimal places)
- Populated by `preloadViewportVoterDetails()` when zooming past heatmap threshold
- Reduces API calls for subsequent popup opens
- Cache is cleared when dataset changes

### API Endpoints Used
- `/api/voters/at?lat=X&lng=Y&election_date=YYYY-MM-DD` - Get voters at specific coordinates
- `/api/voters?county=X&election_date=Y&sw_lat=...&ne_lat=...` - Get voters in viewport (for preloading)
- `/api/voter-history/<vuid>` - Get voting history for a specific voter

### Voting Method Handling
- Frontend: "combined" = aggregated view of all voting methods
- Backend: Only recognizes "early-voting", "election-day", "mail-in"
- Solution: Omit voting_method parameter when dataset is "combined"
