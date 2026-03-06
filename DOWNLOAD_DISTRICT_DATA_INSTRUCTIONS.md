# Instructions: Download District Reference Data

To get the complete list of counties and precincts for all Texas Congressional Districts:

## Step 1: Download the Files

1. Go to: https://data.capitol.texas.gov/dataset/planc2333

2. Download these two files (click the XLS link for each):
   - **PLANC2333_r150.xls** - "Districts by County"
   - **PLANC2333_r365_Prec24G.xls** - "Precincts in District by County"

3. Save both files to: `WhoVoted/data/district_reference/`

## Step 2: Parse the Files

Run the parser script:

```bash
cd WhoVoted
python deploy/parse_district_files.py
```

This will:
- Parse both Excel files
- Extract counties and precincts for all 38 congressional districts
- Create JSON files:
  - `district_counties.json` - Counties per district
  - `district_precincts.json` - Precincts per district (organized by county)
- Display a complete summary showing:
  - How many counties in each district
  - List of all counties
  - How many precincts in each district
  - Precinct counts by county

## What You'll Get

For each of the 38 Texas Congressional Districts (TX-1 through TX-38), you'll see:

```
TX-15 CONGRESSIONAL DISTRICT
================================================================================

COUNTIES: 11
  - Aransas
  - Bee
  - Brooks
  - DeWitt
  - Goliad
  - Gonzales
  - Hidalgo
  - Jim Wells
  - Karnes
  - Lavaca
  - Live Oak

PRECINCTS: 247 across 11 counties
  Aransas: 12 precincts
  Bee: 18 precincts
  Brooks: 8 precincts
  DeWitt: 15 precincts
  Goliad: 9 precincts
  ... and 6 more counties
```

## Files Created

After running the script, you'll have:

- `WhoVoted/data/district_reference/district_counties.json`
- `WhoVoted/data/district_reference/district_precincts.json`

These are the authoritative reference files showing what SHOULD be in each district, independent of where you have voter data.

## Troubleshooting

If the files won't download:
- Try a different browser
- Check if you need to accept terms/conditions on the site
- The files are public data and should be freely accessible

If parsing fails:
- Make sure the files are in the correct directory
- Check that the files aren't corrupted (should be ~100KB-1MB each)
- The script will show detailed error messages
