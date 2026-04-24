# PLANC2333 Complete File Reference

**Source:** Texas Legislature HB4 - 89th Legislature, 2nd Called Session, 2025  
**Location:** `WhoVoted/data/district_reference/`  
**Downloaded:** PLANC2333_All_Files_20251009.zip  
**Applies To:** 2026 elections and beyond (118th Congress districts)

---

## Quick Reference by Use Case

### I need to know: "What counties/precincts/ZIPs are in each district?"
- **PLANC2333_r150.xls** - Counties by district
- **PLANC2333_r365_Prec24G.xls** - Precincts by district
- **PLANC2333_r385.xls** - ZIP codes by district

### I need to: "Validate my voter data against official numbers"
- **PLANC2333_r202_22G-24G.xls** - Official registration & turnout
- **PLANC2333_r100.xls** - Population by district

### I need to: "Analyze demographics"
- **PLANC2333_r116_ACS[Year].xls** - Citizen Voting Age Population
- **PLANC2333_r110_VTD24G.xls** - Population by precinct
- **PLANC2333_r119_ACS[Year]_Election[Year]G.xls** - Hispanic population profile

### I need to: "Look at historical election results"
- **PLANC2333_r206_Election[Year][Type].xls** - District-level results
- **PLANC2333_r211_Election[Year]G.xls** - Results with county subtotals
- **PLANC2333_r237_Election[Year][Type].xls** - Registration & turnout with SSTO

### I need to: "Do geographic/mapping work"
- **PLANC2333.zip** - Shapefile (GIS boundaries)
- **PLANC2333_blk.zip** - Block equivalency file
- **PlanC2333_Map_*.pdf** - Visual maps

---

## Complete File Catalog

### CORE REFERENCE FILES

#### PLANC2333_r100.xls
**Name:** District Population Analysis  
**Contains:** Total population, VAP, demographics by district  
**Columns:** District, Total Pop, VAP, Hispanic %, etc.  
**Use For:**
- Baseline population numbers
- Demographic percentages
- Voting age population
- Context for turnout calculations

**Example Query:** "What's the total population of TX-15?"

---

#### PLANC2333_r110_VTD24G.xls
**Name:** District Population with VTD Subtotals  
**Contains:** Population broken down by Voting Tabulation District (precinct)  
**Columns:** District, County, VTD, Population, Demographics  
**Use For:**
- Precinct-level population data
- Demographic analysis by precinct
- Identifying high-population precincts
- Turnout rate calculations by precinct

**Example Query:** "Which precincts in TX-15 have the highest Hispanic population?"

---

#### PLANC2333_r115_ACS1923.xls
**Name:** District Population Estimates  
**Contains:** American Community Survey population estimates  
**Columns:** District, ACS estimates, margins of error  
**Use For:**
- More recent population estimates than census
- Statistical margins of error
- Demographic projections

**Example Query:** "What's the estimated current population vs 2020 census?"

---

#### PLANC2333_r116_ACS[Year].xls (Multiple Years: 1519, 1620, 1721, 1822, 1923)
**Name:** District ACS Citizen VAP Special Tabulation  
**Contains:** Citizen Voting Age Population from American Community Survey  
**Columns:** District, CVAP by race/ethnicity, age groups  
**Use For:**
- Eligible voter estimates
- Demographic targeting
- Voting Rights Act analysis
- Understanding voter eligibility by demographics

**Example Query:** "How many Hispanic citizens of voting age are in TX-15?"

---

#### PLANC2333_r117_ACS[Year].xls
**Name:** District Block Groups Used in ACS Estimates  
**Contains:** Census block groups used for ACS calculations  
**Columns:** District, Block Group IDs, populations  
**Use For:**
- Understanding ACS methodology
- Fine-grained geographic analysis
- Validating ACS estimates

**Example Query:** "Which block groups were used for TX-15 estimates?"

---

#### PLANC2333_r118_ACS[Year].xls
**Name:** District Population Coverage for ACS Analysis  
**Contains:** Coverage statistics for ACS estimates  
**Columns:** District, coverage percentages, reliability metrics  
**Use For:**
- Assessing ACS data quality
- Understanding estimate reliability
- Identifying data gaps

**Example Query:** "How reliable are the ACS estimates for TX-15?"

---

#### PLANC2333_r119_ACS[Year]_Election[Year]G.xls
**Name:** District Hispanic Population Profile  
**Contains:** Detailed Hispani