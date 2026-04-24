# Commissioner Precinct 2 Vote Count Fix

## Problem
The numbers for Commissioner Precinct 2 (and potentially other commissioner precincts) are incorrect because they were using approximate geographic boundaries instead of the proper precinct-based mapping approach.

## Solution
Updated `deploy/fix_commissioner_precinct_counts.py` to use the same logic as TX-15 district assignment:

1. **Load commissioner precinct boundaries** from `districts.json`
2. **Map voting precincts to commissioner precincts** using polygon containment
   - Get all voting precincts with their centroid locations (average lat/lng of voters)
   - Check which commissioner precinct polygon contains each voting precinct centroid
   - Create mapping: `voting_precinct -> commissioner_precinct_id`
3. **Count only voters in mapped precincts**
   - Query voters table for VUIDs in precincts belonging to each commissioner precinct
   - Count votes from `early_voting` and `election_day` tables for those VUIDs
   - Calculate party breakdown from the actual vote records (not voter registration)
4. **Update district_cache table** with correct counts

## Key Improvements

### Before (Approximate Boundaries)
- Used hardcoded lat/lng boundaries (e.g., "lng > -98.12, lat < 26.44")
- Assigned precincts based on simple coordinate comparisons
- Prone to errors at boundary edges

### After (Polygon-Based Mapping)
- Uses actual GeoJSON polygon boundaries from `districts.json`
- Point-in-polygon algorithm for accurate precinct assignment
- Same approach as TX-15 (proven accurate)
- Party counts from actual vote records, not voter registration

## How to Execute

### Step 1: Upload the Script
```bash
scp WhoVoted/deploy/fix_commissioner_precinct_counts.py ubuntu@whovoted.org:/opt/whovoted/deploy/
```

### Step 2: Run on Server
```bash
ssh ubuntu@whovoted.org
cd /opt/whovoted
python3 deploy/fix_commissioner_precinct_counts.py
```

## Expected Output

The script will:
1. Load 4 commissioner precinct boundaries from `districts.json`
2. Map all voting precincts to commissioner precincts
3. Show precinct assignment summary (e.g., "CPct-2: 45 voting precincts")
4. Calculate statistics for each commissioner precinct:
   - Total registered voters
   - Voters who voted (early + election day)
   - Turnout percentage
   - Party breakdown (DEM/REP)
5. Update `district_cache` table
6. Verify the results

## Database Tables Used

- **voters**: Get VUIDs and their voting_precinct assignments
- **early_voting**: Count early votes and party affiliation
- **election_day**: Count election day votes and party affiliation
- **district_cache**: Store the corrected counts

## What Gets Fixed

The script will correct the counts for all 4 commissioner precincts:
- **CPct-1**: Eastern Hidalgo County
- **CPct-2**: Southern Hidalgo County (the one with incorrect numbers)
- **CPct-3**: Western Hidalgo County
- **CPct-4**: Northern Hidalgo County

## Verification

After running, the script shows:
- Number of voting precincts assigned to each commissioner precinct
- Total voters, votes cast, turnout percentage
- Party breakdown (DEM/REP)
- Cache update timestamp

You can also verify in the database:
```sql
SELECT district_id, total_voters, voted, turnout_percentage, dem_votes, rep_votes
FROM district_cache
WHERE district_type = 'commissioner'
AND county = 'Hidalgo'
AND year = 2026
ORDER BY district_id;
```

## Notes

- The script uses PostgreSQL (not SQLite)
- Database credentials are hardcoded in the script
- The script is idempotent (safe to run multiple times)
- Old cache entries are deleted before inserting new ones
- All changes are committed in a single transaction
