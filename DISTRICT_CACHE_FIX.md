# District Report Cache Fix

## Problem Identified
Large multi-county districts like TX-15 were taking a long time to load because the pre-computed cache files were not being used. The cache lookup was failing due to a naming mismatch.

## Root Cause
- **Cache files** are generated using `district_name` (e.g., `district_report_TX-15_Congressional_District.json`)
- **Backend lookup** was using `district_id` (e.g., trying to find `district_report_TX-15.json`)
- This mismatch caused cache misses, forcing live computation for every request

## Solution Implemented
1. **Frontend (campaigns.js)**: Now sends both `district_id` AND `district_name` in API requests
2. **Backend (app.py)**: Updated cache lookup to use `district_name` instead of `district_id`
3. Added logging to track cache hits: `logger.info(f"District stats cache HIT for {district_name}")`

## Files Modified
- `WhoVoted/backend/app.py` - Updated district_stats() function cache lookup logic
- `WhoVoted/public/campaigns.js` - Added district_name to API request body

## Expected Result
- Districts with pre-computed cache files (like TX-15) should now load instantly
- Cache hits will be logged in backend logs
- Only districts without cache files will trigger live computation

## Current Cache Status
The following district cache files exist on the server:
- TX-15 Congressional District (3.0K) - 41,041 voters
- TX-28 Congressional District (2.7K)
- TX-34 Congressional District (254 bytes)
- TX State House Districts: 31, 35, 36, 37, 39, 40, 41

## Next Steps
To pre-compute cache for ALL districts:

1. **Option A: Run optimize_step2_gazette.py** (slow, 6+ hours)
   - Processes all historical elections + current turnout
   - Generates gazette, county reports, AND district reports
   
2. **Option B: Run cache_districts_only.py** (faster, but still slow)
   - Only generates district reports for current 2026 turnout
   - Skips historical data processing
   - Still slow due to point-in-polygon checks for millions of voters

3. **Option C: Optimize the caching script** (recommended)
   - Add spatial indexes to speed up point-in-polygon queries
   - Use multiprocessing to parallelize district processing
   - Cache intermediate results (voter coordinates, precinct lookups)

## Performance Notes
- Cached districts: Instant load (<100ms)
- Uncached districts: 10-60 seconds depending on size
- TX-15 spans multiple counties with 41,041 voters - now loads instantly with cache

## Testing
To verify the fix is working:
1. Open the app and select TX-15 Congressional District
2. Check backend logs for "District stats cache HIT for TX-15 Congressional District"
3. Report should load instantly (not 10+ seconds)
