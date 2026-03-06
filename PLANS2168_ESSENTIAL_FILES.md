# Essential Files from PLANS2168 Data Portal

Source: https://data.capitol.texas.gov/dataset/plans2168

## Overview

PLANS2168 contains data for Texas State Senate Districts (31 districts) for the 2023-2026 election cycle. The file structure mirrors PLANC2333 (Congressional Districts), making it easy to use the same parsing tools.

## Priority 1: Core Reference Data (MUST HAVE)

### 1. PLANS2168_r150.xls - Districts by County
**Purpose:** Shows which counties are in each State Senate district
**Use:** Determine total counties per district, identify split counties
**Format:** Excel spreadsheet
**Your Need:** HIGH - This is the authoritative source for county membership

### 2. PLANS2168_r365_Prec24G.xls - Precincts in District by County
**Purpose:** Lists all precincts in each district, organized by county
**Use:** Determine total precincts per district, validate precinct assignments
**Format:** Excel spreadsheet
**Your Need:** HIGH - Essential for precinct-level analysis
**Note:** Multiple versions available for different elections (2020 General, 2022 Primary, 2022 General, 2024 Primary, 2024 General)

### 3. PLANS2168_r385_2024.xls - ZIP Codes by District
**Purpose:** Lists ZIP codes in each State Senate district
**Use:** ZIP code lookup, address validation, geographic coverage
**Format:** Excel spreadsheet
**Your Need:** MEDIUM - Useful for address-based queries
**Note:** Also available for 2020 (r385_2020.xls)

## Priority 2: Population & Demographics

### 4. PLANS2168r100.xls - District Population Analysis
**Purpose:** Total population, voting age population, demographics by district
**Use:** Context for voter turnout calculations, demographic analysis
**Format:** Excel spreadsheet
**Your Need:** MEDIUM - Good for contextual data

### 5. PLANS2168_r202_22G-24G.xls - District Population and Voter Data
**Purpose:** Population + voter registration + turnout data by district
**Use:** Benchmark your data against official registration numbers
**Format:** Excel spreadsheet
**Your Need:** HIGH - Validate your voter counts
**Note:** Also available for 18G-20G and 20G-22G

## Priority 3: Election Analysis

### 6. PLANS2168_r206_Election24G.xls - District Election Analysis
**Purpose:** 2024 General Election results by district
**Use:** Historical election performance
**Format:** Excel spreadsheet
**Your Need:** MEDIUM - Useful for historical context
**Note:** Available for multiple elections (12DP, 12DR, 12G, 12RP, 12RR, 14DP, 14DR, 14G, 14RP, 14RR, 16DP, 16DR, 16G, 16RP, 16RR, 18DP, 18DR, 18G, 18RP, 20DP, 20DR, 20G, 20RP, 22DP, 22DR, 22G, 22RP, 22RR, 24DP, 24G, 24RP)

### 7. PLANS2168_r237_Election24G.xls - District Pop, Voter Registration, and Turnout with SSTO
**Purpose:** Comprehensive voter registration and turnout statistics
**Use:** Benchmark turnout rates, registration vs turnout gaps
**Format:** Excel spreadsheet
**Your Need:** MEDIUM - For turnout modeling
**Note:** Available for multiple elections

## Priority 4: Geographic Data

### 8. PLANS2168.zip - Shapefile
**Purpose:** GIS boundaries for all State Senate districts
**Use:** Spatial analysis, mapping, geographic queries
**Format:** Shapefile (requires GIS software)
**Your Need:** MEDIUM - If you want to do spatial joins or mapping

### 9. PLANS2168_blk.zip - Block Equivalency
**Purpose:** Maps census blocks to State Senate districts
**Use:** Fine-grained geographic analysis, address-to-district lookup
**Format:** Text file with block assignments
**Your Need:** LOW - Only if doing detailed geographic work

### 10. PLANS2168_kml.zip - KML File
**Purpose:** Google Earth/Maps compatible district boundaries
**Use:** Visualization in Google Earth, web mapping
**Format:** KML (Keyhole Markup Language)
**Your Need:** LOW - For visualization only

## Priority 5: Split Geography

### 11. PLANS2168_r155.xls - Split Counties
**Purpose:** Lists counties that are divided between multiple districts
**Use:** Identify which counties are partially in each district
**Format:** Excel spreadsheet
**Your Need:** MEDIUM - Helps understand partial county assignments

### 12. PLANS2168_r370_Prec2024 General.xls - Split Precincts in District by County
**Purpose:** Lists precincts that are divided between districts
**Use:** Identify split precincts (rare but important)
**Format:** Excel spreadsheet
**Your Need:** LOW - Only matters if you have split precinct data

### 13. PLANS2168_r380_Prec2024 General.xls - Split Precincts by District
**Purpose:** Alternative view of split precincts
**Use:** Cross-reference split precinct data
**Format:** Excel spreadsheet
**Your Need:** LOW - Redundant with r370

## Priority 6: Other Useful Files

### 14. PLANS2168r125.xls - Cities and CDPs by District
**Purpose:** Lists cities and Census Designated Places in each district
**Use:** City-level analysis, urban vs rural breakdowns
**Format:** Excel spreadsheet
**Your Need:** LOW - Nice to have for geographic context

### 15. PLANS2168r130.xls - Split Cities and CDPs by District
**Purpose:** Cities divided between multiple districts
**Use:** Understand city-level splits
**Format:** Excel spreadsheet
**Your Need:** LOW - Reference information

### 16. PLANS2168_r350_20230301.xls - Incumbents by District
**Purpose:** Lists current State Senators for each district
**Use:** Campaign context, incumbent information
**Format:** Excel spreadsheet
**Your Need:** LOW - Reference information

## Recommended Download List

For your immediate needs, download these files in order:

1. **PLANS2168_r150.xls** (Districts by County) - CRITICAL
2. **PLANS2168_r365_Prec2024 General.xls** (Precincts by District) - CRITICAL
3. **PLANS2168_r202_22G-24G.xls** (Population and Voter Data) - HIGH VALUE
4. **PLANS2168_r385_2024.xls** (ZIP Codes) - USEFUL
5. **PLANS2168_r155.xls** (Split Counties) - USEFUL
6. **PLANS2168.zip** (Shapefile) - IF DOING GIS WORK

## How These Files Help Your System

### For Campaign Reports:
- **r150** → Show "District covers X counties"
- **r365** → Show "District has Y precincts"
- **r202** → Compare your voter counts to official registration
- **r155** → Identify which counties are partially in district

### For Data Validation:
- **r202** → "We have data for X voters. Official registration: Y"
- **r150** → "District covers X counties. We have data for Y counties (Z%)"
- **r365** → "District has X precincts. We have data for Y precincts (Z%)"

### For User Queries:
- **r385** → "What district is ZIP code 78539 in?"
- **r150** → "What counties are in SD-27?"
- **r365** → "What precincts are in Hidalgo County for SD-27?"

## File Naming Convention

The "r" numbers indicate report types (same as Congressional):
- **r100-r199**: Population and demographic reports
- **r200-r299**: Election and voter data reports
- **r300-r399**: Geographic and compactness reports
- **r365-r385**: Precinct and ZIP code reports

## Key Differences from Congressional Districts

1. **31 districts instead of 38** - State Senate has fewer, larger districts
2. **More split counties** - Senate districts often span multiple counties
3. **Longer terms** - State Senators serve 4-year terms (vs 2-year for House)
4. **Different election cycles** - Some Senate districts elect in presidential years, others in midterms

## Bulk Download Option

The portal offers:
- **PLANS2168_All_Files_20250220.zip** - Downloads everything at once
- Contains all XLS, PDF, and shapefile data
- One-time download, extract what you need

## Integration with Existing Parser

The existing `deploy/parse_district_files.py` script can be updated to handle PLANS2168 files:

```python
# Add support for State Senate districts
senate_counties_file = data_dir / "PLANS2168_r150.xls"
if senate_counties_file.exists():
    senate_counties_data = parse_counties_file(senate_counties_file)
    if senate_counties_data:
        output_file = data_dir / "state_senate_counties.json"
        with open(output_file, 'w') as f:
            json.dump(senate_counties_data, f, indent=2)
```

## Next Steps

1. Download Phase 1 files (r150, r365, r202, r385, r155)
2. Save to `WhoVoted/data/district_reference/plans2168/`
3. Update `python deploy/parse_district_files.py` to handle PLANS2168
4. This creates comprehensive JSON reference files for all 31 State Senate districts

These become your authoritative reference for what SHOULD be in each State Senate district, independent of where you have voter data.

## Related Files

### State House Districts (150 districts):
- Portal: https://data.capitol.texas.gov/dataset/planh2316
- Files: PLANH2316_r150.xls, PLANH2316_r365.xls, etc.
- Same file structure as Congressional and Senate districts

### Congressional Districts (38 districts):
- Portal: https://data.capitol.texas.gov/dataset/planc2333
- Documentation: See `PLANC2333_ESSENTIAL_FILES.md`
