# Commissioner Precinct 2 Vote Count Discrepancy

## Problem
Database shows 22,851 DEM votes for CPct-2, but certified numbers are 13,999 DEM votes.

## Analysis Results

### Current Database (county-upload source only)
- DEM Early Voting: 16,321
- DEM Election Day: 3,874
- DEM Total: 20,195
- Precincts included: 422

### Certified Numbers
- DEM Early Voting: 9,876
- DEM Election Day: 3,754
- DEM Total: 13,630 (user said 13,999, but 9876+3754=13,630)

### Discrepancy
- Early voting: 6,445 extra votes (65% more than certified)
- Election day: 120 extra votes (3% more than certified)
- Overall: Database has 1.65x more votes than certified

## Root Cause
The CPct-2 boundary polygon in `districts.json` includes 422 voting precincts, but the certified numbers suggest only ~255 precincts should be included (422 * 0.605 = 255).

**The boundary is too large and includes precincts that are not actually in Commissioner Precinct 2.**

## Solutions

### Option 1: Correct the Boundary (RECOMMENDED)
Obtain the official CPct-2 boundary shapefile from Hidalgo County and regenerate the polygon in `districts.json`.

### Option 2: Provide Correct Precinct List
If you have the official list of precincts in CPct-2, we can:
1. Filter to only those precincts
2. Recalculate the boundary based on those precincts
3. Update `districts.json`

### Option 3: Manual Override
Create a precinct mapping file that explicitly lists which precincts belong to CPct-2.

## Next Steps
Please provide ONE of the following:
1. Official CPct-2 boundary shapefile
2. Official list of precincts in CPct-2
3. Confirmation that the current boundary is correct (then we need to investigate data source)

## Diagnostic Scripts Created
- `deploy/diagnose_cpct2_discrepancy.py` - Shows vote breakdown by method and party
- `deploy/verify_cpct2_election.py` - Checks election types and data sources
- `deploy/analyze_cpct2_precincts.py` - Lists all 422 precincts and their votes
- `deploy/find_correct_cpct2_filter.py` - Tests different filtering approaches
