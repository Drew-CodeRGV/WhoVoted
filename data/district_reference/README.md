# District Reference Data

This directory contains authoritative reference data for Texas legislative districts.

## Purpose

These files define what counties, precincts, and ZIP codes SHOULD be in each district according to official redistricting plans, independent of where we have voter data.

## Files

### congressional_districts.json
- **Source:** HB4 PlanC2333 (89th Legislature, 2nd C.S., 2025)
- **Contains:** Counties per congressional district (38 districts)
- **Status:** TX-15 verified (11 counties), others pending
- **Use:** Show "District covers X counties, we have data for Y counties"

### Future Files (To Be Created)
- `congressional_precincts.json` - Precincts per district
- `congressional_zipcodes.json` - ZIP codes per district
- `state_senate_districts.json` - State Senate (31 districts)
- `state_house_districts.json` - State House (150 districts)

## Data Sources

### Congressional Districts (38 districts)
- Portal: https://data.capitol.texas.gov/dataset/planc2333
- Plan: PLANC2333 (HB4, 2025)
- Key Files:
  - PLANC2333_r150.xls - Counties by district
  - PLANC2333_r365_Prec24G.xls - Precincts by district
  - PLANC2333_r385.xls - ZIP codes by district

### State Senate (31 districts)
- Portal: https://data.capitol.texas.gov/dataset/plans2168
- Plan: PLANS2168 (SB4, 2025)

### State House (150 districts)
- Portal: https://data.capitol.texas.gov/dataset/planh2316
- Plan: PLANH2316 (HB1, 2025)

## How to Update

1. Download files from data portal
2. Save to this directory
3. Run: `python deploy/parse_district_files.py`
4. This creates/updates the JSON reference files

## Example: TX-15

According to HB4 PlanC2333, TX-15 includes:

**11 counties total:**
- 9 full counties: Bee, Brooks, DeWitt, Goliad, Gonzales, Jim Wells, Karnes, Lavaca, Live Oak
- 2 partial counties: Aransas, Hidalgo

This is the authoritative count, regardless of where we have voter data.

## Usage in Code

```python
import json

# Load reference data
with open('data/district_reference/congressional_districts.json') as f:
    districts = json.load(f)

# Get district info
tx15 = districts['15']
print(f"TX-15 covers {tx15['total_counties']} counties")
print(f"Counties: {', '.join(tx15['counties'])}")

# Compare to actual data
actual_counties = get_counties_with_data('15')
coverage = len(actual_counties) / tx15['total_counties'] * 100
print(f"Data coverage: {coverage:.1f}%")
```

## Verification

To verify the data:
1. Check official redistricting bill text
2. Cross-reference with Texas Legislature maps
3. Compare with county election administrator records

## Last Updated

2026-03-06 - Initial creation with TX-15 data
