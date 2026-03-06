# Essential Files from PLANC2333 Data Portal

Source: https://data.capitol.texas.gov/dataset/planc2333

## Priority 1: Core Reference Data (MUST HAVE)

### 1. PLANC2333_r150.xls - Districts by County
**Purpose:** Shows which counties are in each congressional district
**Use:** Determine total counties per district, identify split counties
**Format:** Excel spreadsheet
**Your Need:** HIGH - This is the authoritative source for county membership

### 2. PLANC2333_r365_Prec24G.xls - Precincts in District by County
**Purpose:** Lists all precincts in each district, organized by county
**Use:** Determine total precincts per district, validate precinct assignments
**Format:** Excel spreadsheet
**Your Need:** HIGH - Essential for precinct-level analysis

### 3. PLANC2333_r385.xls - ZIP Codes by District
**Purpose:** Lists ZIP codes in each congressional district
**Use:** ZIP code lookup, address validation, geographic coverage
**Format:** Excel spreadsheet
**Your Need:** MEDIUM - Useful for address-based queries

## Priority 2: Population & Demographics

### 4. PLANC2333_r100.xls - District Population Analysis
**Purpose:** Total population, voting age population, demographics by district
**Use:** Context for voter turnout calculations, demographic analysis
**Format:** Excel spreadsheet
**Your Need:** MEDIUM - Good for contextual data

### 5. PLANC2333_r202_22G-24G.xls - District Population and Voter Data
**Purpose:** Population + voter registration + turnout data by district
**Use:** Benchmark your data against official registration numbers
**Format:** Excel spreadsheet
**Your Need:** HIGH - Validate your voter counts

## Priority 3: Election Analysis

### 6. PLANC2333_r211_Election24G.xls - Election Analysis with County Subtotals
**Purpose:** 2024 General Election results by district with county breakdowns
**Use:** Historical election performance, county-level results
**Format:** Excel spreadsheet
**Your Need:** MEDIUM - Useful for historical context

### 7. PLANC2333_r206_Election24G.xls - District Election Analysis
**Purpose:** Detailed 2024 election results by district
**Use:** Historical voting patterns, partisan performance
**Format:** Excel spreadsheet
**Your Need:** LOW - Historical reference only

## Priority 4: Geographic Data

### 8. PLANC2333.zip - Shapefile
**Purpose:** GIS boundaries for all congressional districts
**Use:** Spatial analysis, mapping, geographic queries
**Format:** Shapefile (requires GIS software)
**Your Need:** MEDIUM - If you want to do spatial joins or mapping

### 9. PLANC2333_blk.zip - Block Equivalency
**Purpose:** Maps census blocks to congressional districts
**Use:** Fine-grained geographic analysis, address-to-district lookup
**Format:** Text file with block assignments
**Your Need:** LOW - Only if doing detailed geographic work

## Priority 5: Split Geography

### 10. PLANC2333_r155.xls - Split Counties
**Purpose:** Lists counties that are divided between multiple districts
**Use:** Identify which counties are partially in each district
**Format:** Excel spreadsheet
**Your Need:** MEDIUM - Helps understand partial county assignments

### 11. PLANC2333_r370_Prec24G.xls - Split Precincts in District by County
**Purpose:** Lists precincts that are divided between districts
**Use:** Identify split precincts (rare but important)
**Format:** Excel spreadsheet
**Your Need:** LOW - Only matters if you have split precinct data

## Priority 6: Other Useful Files

### 12. PLANC2333_r125.xls - Cities and CDPs by District
**Purpose:** Lists cities and Census Designated Places in each district
**Use:** City-level analysis, urban vs rural breakdowns
**Format:** Excel spreadsheet
**Your Need:** LOW - Nice to have for geographic context

### 13. PLANC2333_r350.xls - Incumbents by District
**Purpose:** Lists current representatives for each district
**Use:** Campaign context, incumbent information
**Format:** Excel spreadsheet
**Your Need:** LOW - Reference information

## Recommended Download List

For your immediate needs, download these files in order:

1. **PLANC2333_r150.xls** (Districts by County) - CRITICAL
2. **PLANC2333_r365_Prec24G.xls** (Precincts by District) - CRITICAL
3. **PLANC2333_r202_22G-24G.xls** (Population and Voter Data) - HIGH VALUE
4. **PLANC2333_r385.xls** (ZIP Codes) - USEFUL
5. **PLANC2333_r155.xls** (Split Counties) - USEFUL
6. **PLANC2333.zip** (Shapefile) - IF DOING GIS WORK

## How These Files Help Your System

### For Campaign Reports:
- **r150** → Show "District covers X counties"
- **r365** → Show "District has Y precincts"
- **r202** → Compare your voter counts to official registration
- **r155** → Identify which counties are partially in district

### For Data Validation:
- **r202** → "We have data for 52,580 voters. Official registration: 487,000"
- **r150** → "District covers 11 counties. We have data for 2 counties (18%)"
- **r365** → "District has 247 precincts. We have data for 89 precincts (36%)"

### For User Queries:
- **r385** → "What district is ZIP code 78539 in?"
- **r150** → "What counties are in TX-15?"
- **r365** → "What precincts are in Hidalgo County for TX-15?"

## File Naming Convention

The "r" numbers indicate report types:
- **r100-r199**: Population and demographic reports
- **r200-r299**: Election and voter data reports
- **r300-r399**: Geographic and compactness reports
- **r365-r385**: Precinct and ZIP code reports

## Priority 7: Future Features & Advanced Analysis

### 14. PLANC2333_r110_VTD24G.xls - District Population with VTD Subtotals
**Purpose:** Population broken down by Voting Tabulation District (precinct)
**Use:** Precinct-level demographic analysis, turnout rate calculations
**Format:** Excel spreadsheet
**Your Need:** FUTURE - For precinct-level demographic overlays
**Use Case:** "Show me precincts with high Hispanic population and low turnout"

### 15. PLANC2333_r116_ACS1923.xls - District ACS Citizen VAP Special Tabulation
**Purpose:** American Community Survey data - Citizen Voting Age Population
**Use:** Demographic analysis, eligible voter estimates
**Format:** Excel spreadsheet
**Your Need:** FUTURE - For demographic targeting
**Use Case:** "What's the demographic profile of voters we're missing?"

### 16. PLANC2333_r160_ISDsSY24-25.xls - School Districts by District
**Purpose:** Maps school districts to congressional districts
**Use:** Education-focused campaigns, school board coordination
**Format:** Excel spreadsheet
**Your Need:** FUTURE - For education-related campaigns
**Use Case:** "Which school districts are in TX-15?"

### 17. PLANC2333_r211_Election[Year]G.xls - Election Analysis with County Subtotals
**Purpose:** Historical election results by county within each district
**Use:** County-level performance trends, swing analysis
**Format:** Excel spreadsheet (multiple years available: 2012, 2014, 2016, 2018, 2020, 2022, 2024)
**Your Need:** FUTURE - For historical trend analysis
**Use Case:** "Show me how each county in TX-15 voted in the last 5 elections"

### 18. PLANC2333_r237_Election24G.xls - District Pop, Voter Registration, and Turnout with SSTO
**Purpose:** Comprehensive voter registration and turnout statistics
**Use:** Benchmark turnout rates, registration vs turnout gaps
**Format:** Excel spreadsheet
**Your Need:** FUTURE - For turnout modeling
**Use Case:** "What's the registration-to-turnout conversion rate by district?"

### 19. PLANC2333.zip - Shapefile (GIS Boundaries)
**Purpose:** Actual geographic boundaries of districts
**Use:** Spatial analysis, custom mapping, address-to-district lookup
**Format:** Shapefile (requires GIS software or GeoPandas)
**Your Need:** FUTURE - For advanced geographic features
**Use Case:** "Show me a heat map of voter density within TX-15"

### 20. PLANC2333_blk.zip - Block Equivalency File
**Purpose:** Maps every census block to its congressional district
**Use:** Precise address-to-district assignment, fine-grained analysis
**Format:** Text file with block assignments
**Your Need:** FUTURE - For address validation
**Use Case:** "Verify this address is actually in TX-15"

### 21. PlanC2333_Map_Report_Package.pdf - Complete Map Package
**Purpose:** Visual maps of all districts with overlays
**Use:** Reference, presentations, visual verification
**Format:** PDF with maps
**Your Need:** FUTURE - For presentations and documentation
**Use Case:** "Show me what TX-15 looks like on a map"

### 22. PLANC2333_r315.xls - District Compactness Analysis
**Purpose:** Compactness scores and geometric analysis of districts
**Use:** Gerrymandering analysis, district shape metrics
**Format:** Excel spreadsheet
**Your Need:** FUTURE - For political analysis
**Use Case:** "How gerrymandered is TX-15?"

### 23. PLANC2333_r130.xls - Split Cities and CDPs by District
**Purpose:** Cities that are divided between multiple districts
**Use:** Understand city-level splits, urban analysis
**Format:** Excel spreadsheet
**Your Need:** FUTURE - For city-focused campaigns
**Use Case:** "Which parts of McAllen are in TX-15 vs TX-34?"

## Advanced Use Cases by File

### For Voter Targeting:
- **r116** (Demographics) → "Target Hispanic voters age 25-34 in low-turnout precincts"
- **r110** (VTD Population) → "Find precincts with high population but low registration"
- **r237** (Registration/Turnout) → "Identify registration-turnout gaps by precinct"

### For Campaign Strategy:
- **r211** (Historical Results) → "Which counties are trending Democratic?"
- **r202** (Voter Data) → "Where should we focus GOTV efforts?"
- **r160** (School Districts) → "Coordinate with school board candidates"

### For Data Validation:
- **Shapefile** → "Verify our precinct boundaries are correct"
- **Block Equivalency** → "Validate address-to-district assignments"
- **r155** (Split Counties) → "Confirm which part of Hidalgo is in TX-15"

### For Reporting & Visualization:
- **Map Package PDF** → "Show district boundaries in presentations"
- **r315** (Compactness) → "Analyze district shapes"
- **r125** (Cities) → "List all cities in the district"

## Complete Download Strategy

### Phase 1: Immediate (Download Now)
1. PLANC2333_r150.xls (Counties)
2. PLANC2333_r365_Prec24G.xls (Precincts)
3. PLANC2333_r202_22G-24G.xls (Voter Data)
4. PLANC2333_r385.xls (ZIP Codes)
5. PLANC2333_r155.xls (Split Counties)

### Phase 2: Near-Term (Download Soon)
6. PLANC2333_r110_VTD24G.xls (VTD Population)
7. PLANC2333_r237_Election24G.xls (Registration/Turnout)
8. PLANC2333_r211_Election24G.xls (County Results)
9. PLANC2333.zip (Shapefile)

### Phase 3: Future Features (Download When Needed)
10. PLANC2333_r116_ACS1923.xls (Demographics)
11. PLANC2333_r160_ISDsSY24-25.xls (School Districts)
12. PLANC2333_blk.zip (Block Equivalency)
13. PlanC2333_Map_Report_Package.pdf (Maps)
14. Historical election files (r211 for 2012-2022)

## Storage Recommendation

Create a structured directory:
```
WhoVoted/data/district_reference/
├── planc2333/
│   ├── core/              # Phase 1 files
│   ├── analysis/          # Phase 2 files
│   ├── advanced/          # Phase 3 files
│   └── shapefiles/        # GIS data
```

## Similar Files for State Districts

### State Senate (31 districts):
- Portal: https://data.capitol.texas.gov/dataset/plans2168
- Files: PLANS2168_r150.xls, PLANS2168_r365.xls, etc.
- Same file structure as congressional districts

### State House (150 districts):
- Portal: https://data.capitol.texas.gov/dataset/planh2316
- Files: PLANH2316_r150.xls, PLANH2316_r365.xls, etc.
- Same file structure as congressional districts

## Next Steps

1. Download Phase 1 files (r150, r365, r202, r385, r155)
2. Save to `WhoVoted/data/district_reference/planc2333/core/`
3. Run `python deploy/parse_district_files.py`
4. This creates comprehensive JSON reference files for all 38 districts

The parser script will handle multiple file types and create:
- `district_counties.json` - Counties per district
- `district_precincts.json` - Precincts per district by county
- `district_zipcodes.json` - ZIP codes per district
- `district_voter_stats.json` - Official registration numbers

These become your authoritative reference for what SHOULD be in each district, independent of where you have voter data.

## Pro Tip: Bulk Download

The portal offers:
- **PLANC2333_All_Files_20251009.zip** - Downloads everything at once
- Size: ~500MB compressed
- Contains all XLS, PDF, and shapefile data
- One-time download, extract what you need
