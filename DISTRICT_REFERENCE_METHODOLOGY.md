# District Reference Data Methodology

## Purpose

This document explains how to determine the authoritative list of counties, precincts, and ZIP codes that belong to each Texas Congressional District, independent of where we have voter data.

## The Problem

Previously, the system only showed counties where we had voter data. For example, TX-15 was showing only 2 counties (Hidalgo and Brooks) because those were the only counties with uploaded voter files. However, TX-15 actually covers 11 counties according to the official redistricting plan.

## The Solution

Use the official Texas Legislature redistricting data as the authoritative source for district boundaries.

## Data Source

**Official Source:** Texas Legislature Redistricting Data Portal  
**URL:** https://data.capitol.texas.gov/dataset/planc2333  
**Plan:** PLANC2333 (Enacted by 89th Legislature, 2nd C.S., 2025)

### Key Files

1. **PLANC2333_r150.xls** - Districts by County
   - Shows which counties are in each district
   - Indicates which counties are split (partially in district)
   
2. **PLANC2333_r365_Prec24G.xls** - Precincts in District by County
   - Shows which precincts are in each district
   - Organized by county
   
3. **PLANC2333_r385.xls** - ZIP Codes by District
   - Shows which ZIP codes are in each district

## How to Determine Counties in a District

### Method 1: Download Official Files (Recommended)

1. Go to https://data.capitol.texas.gov/dataset/planc2333
2. Download `PLANC2333_r150.xls` (Districts by County)
3. Open in Excel/LibreOffice
4. Find the district number (e.g., "15" for TX-15)
5. Count all counties listed for that district
6. Note which counties are marked as "split" or "partial"

### Method 2: Use the Redistricting Bill Text

1. Go to https://capitol.texas.gov
2. Search for "HB 4" from the 89th Legislature, 2nd Called Session
3. Read the bill text for the specific district
4. Count all counties mentioned (both full and partial)

### Method 3: Use Redistricting Maps

1. Go to https://dvr.capitol.texas.gov/Congress/0/PLANC2333
2. View the interactive map
3. Identify all counties that the district touches
4. This is visual confirmation but less precise than the data files

## Example: TX-15

According to HB4 PlanC2333, TX-15 includes:

**Full Counties (9):**
1. Bee County
2. Brooks County
3. DeWitt County
4. Goliad County
5. Gonzales County
6. Jim Wells County
7. Karnes County
8. Lavaca County
9. Live Oak County

**Partial Counties (2):**
10. Aransas County (portions)
11. Hidalgo County (portions)

**Total: 11 counties**

## Implementation

### Reference Data Files

Store authoritative district reference data in:
- `WhoVoted/data/district_reference/district_counties.json`
- `WhoVoted/data/district_reference/district_precincts.json`
- `WhoVoted/data/district_reference/district_zipcodes.json`

### Usage in Reports

When generating campaign reports or district summaries:

1. **Load reference data** to know what SHOULD be in the district
2. **Query voter data** to see what we HAVE data for
3. **Show both**:
   - "District covers X counties"
   - "We have voting data for Y counties"
   - "Missing data for Z counties"

### Example Report Card

```
TX-15 Congressional District Report Card

DISTRICT COVERAGE:
- Total counties in district: 11
- Counties with voting data: 2 (18%)
- Missing data: 9 counties

COUNTIES IN DISTRICT:
✓ Hidalgo County (partial) - 51,914 voters (98.7%)
✓ Brooks County - 666 voters (1.3%)
○ Aransas County (partial) - NO DATA
○ Bee County - NO DATA
○ DeWitt County - NO DATA
○ Goliad County - NO DATA
○ Gonzales County - NO DATA
○ Jim Wells County - NO DATA
○ Karnes County - NO DATA
○ Lavaca County - NO DATA
○ Live Oak County - NO DATA

PRECINCTS:
- Total precincts in district: [from reference data]
- Precincts with voting data: [from database]
- Data coverage: X%
```

## Automation Script

The script `deploy/build_district_reference_data.py` attempts to download and parse the official files automatically. If download fails due to SSL or access issues, manually download the files and run the parser.

## Update Frequency

District boundaries change when:
1. New redistricting legislation is passed
2. Court orders modify districts
3. Census data triggers redistricting

**Current Plan:** PLANC2333 (2025)  
**Next Expected Update:** After 2030 Census

## Validation

To validate the reference data:
1. Cross-reference with official redistricting maps
2. Compare with Texas Secretary of State data
3. Verify against county election administrator records
4. Check that precinct counts match county totals

## Notes

- A "split county" means only part of the county is in the district
- Precinct boundaries can cross district lines (split precincts)
- ZIP codes are approximations and may not align perfectly with district boundaries
- Always use the most recent enacted plan (currently PLANC2333)
