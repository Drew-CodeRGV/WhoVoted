# State Senate District Reference System - Implementation Summary

**Date:** March 6, 2026  
**Status:** ✓ Complete

## What Was Built

Created a parallel reference data system for Texas State Senate districts (31 districts) that mirrors the Congressional district system (38 districts).

## Files Created

### 1. state_senate_districts.json
- Main reference file for all 31 State Senate districts
- Structure matches congressional_districts.json
- All districts initialized with empty data (pending population from XLS files)
- Location: `WhoVoted/data/district_reference/state_senate_districts.json`

### 2. PLANS2168_ESSENTIAL_FILES.md
- Complete guide to State Senate district data files
- Mirrors PLANC2333_ESSENTIAL_FILES.md structure
- Documents all available files at https://data.capitol.texas.gov/dataset/plans2168
- Priority-ranked file list with use cases
- Location: `WhoVoted/PLANS2168_ESSENTIAL_FILES.md`

### 3. DISTRICT_REFERENCE_COMPLETE_GUIDE.md
- Comprehensive guide covering both Congressional and State Senate systems
- Quick start instructions for both district types
- Code examples for integration
- Troubleshooting guide
- Location: `WhoVoted/DISTRICT_REFERENCE_COMPLETE_GUIDE.md`

### 4. Updated parse_district_files.py
- Now handles both PLANC2333 (Congressional) and PLANS2168 (State Senate)
- Automatically detects and parses both district types
- Creates separate output files for each:
  - `congressional_counties.json` / `state_senate_counties.json`
  - `congressional_precincts.json` / `state_senate_precincts.json`
- Location: `WhoVoted/deploy/parse_district_files.py`

## Data Sources

### State Senate Districts (PLANS2168)
- **Portal:** https://data.capitol.texas.gov/dataset/plans2168
- **Legislature:** 88th Legislature, Regular Session, 2023
- **Effective:** 2023-2026 elections
- **Total Districts:** 31

### Key Files to Download
1. **PLANS2168_r150.xls** - Districts by County (CRITICAL)
2. **PLANS2168_r365_Prec2024 General.xls** - Precincts by District (CRITICAL)
3. **PLANS2168_r202_22G-24G.xls** - Voter Data (HIGH VALUE)
4. **PLANS2168_r385_2024.xls** - ZIP Codes (USEFUL)
5. **PLANS2168_r155.xls** - Split Counties (USEFUL)

## How to Use

### Step 1: Download Files
```bash
# Go to https://data.capitol.texas.gov/dataset/plans2168
# Download the 5 key files listed above
# Save to: WhoVoted/data/district_reference/
```

### Step 2: Parse the Data
```bash
cd WhoVoted
python deploy/parse_district_files.py
```

### Step 3: Verify Output
The parser will create:
- `state_senate_counties.json` - Counties per district
- `state_senate_precincts.json` - Precincts per district by county

## System Architecture

```
District Reference System
├── Congressional Districts (38)
│   ├── Data Source: PLANC2333
│   ├── Reference: congressional_districts.json
│   ├── Parsed: congressional_counties.json
│   └── Parsed: congressional_precincts.json
│
├── State Senate Districts (31)
│   ├── Data Source: PLANS2168
│   ├── Reference: state_senate_districts.json
│   ├── Parsed: state_senate_counties.json
│   └── Parsed: state_senate_precincts.json
│
└── State House Districts (150) - Future
    ├── Data Source: PLANH2316
    └── Same structure as above
```

## Key Features

### 1. Unified Parser
- Single script handles all district types
- Automatic column detection
- Error handling for malformed data
- Comprehensive summary output

### 2. Consistent Structure
- All district types use same JSON schema
- Easy to extend to State House districts
- Backwards compatible with existing code

### 3. Complete Documentation
- Essential files guide for each district type
- Complete integration guide
- Code examples for common use cases
- Troubleshooting section

## Integration Points

### Backend (reports.py)
```python
# Load State Senate reference
with open('data/district_reference/state_senate_districts.json') as f:
    STATE_SENATE_REF = json.load(f)

def get_senate_district_coverage(district_num):
    reference = STATE_SENATE_REF.get(str(district_num), {})
    # Calculate coverage same as Congressional
```

### Frontend (dashboard.js)
```javascript
// Add district type selector
<select id="districtType">
  <option value="congressional">Congressional</option>
  <option value="senate">State Senate</option>
  <option value="house">State House</option>
</select>
```

## Comparison: Congressional vs State Senate

| Feature | Congressional | State Senate |
|---------|--------------|--------------|
| Total Districts | 38 | 31 |
| Data Portal | PLANC2333 | PLANS2168 |
| Term Length | 2 years | 4 years |
| File Structure | Same | Same |
| Parser Support | ✓ | ✓ |

## Next Steps

### Immediate
1. Download PLANS2168 files from data portal
2. Run parser to populate state_senate_counties.json
3. Verify all 31 districts are parsed correctly

### Short-term
1. Integrate State Senate reference into reports module
2. Add State Senate district selector to frontend
3. Update coverage metrics to show both district types

### Long-term
1. Add State House districts (PLANH2316)
2. Create unified district lookup API
3. Add GIS integration for precise address-to-district mapping

## File Naming Convention

Both Congressional and State Senate use the same "r" number system:

- **r100-r199**: Population and demographic reports
- **r200-r299**: Election and voter data reports
- **r300-r399**: Geographic and compactness reports
- **r365-r385**: Precinct and ZIP code reports

This consistency makes it easy to work with both district types.

## Git Commit

All changes synced to GitHub:
```
commit becfdf7
Add State Senate district reference system (PLANS2168)

- Created state_senate_districts.json with all 31 districts
- Created PLANS2168_ESSENTIAL_FILES.md guide
- Updated parse_district_files.py to handle both Congressional and State Senate
- Created DISTRICT_REFERENCE_COMPLETE_GUIDE.md comprehensive documentation
- Parser now supports PLANC2333 (Congressional) and PLANS2168 (State Senate)
- Ready to download and parse State Senate district data
```

## Success Criteria

✓ State Senate reference file created (31 districts)  
✓ Essential files guide documented  
✓ Parser updated to handle both district types  
✓ Complete integration guide created  
✓ All files synced to GitHub  
✓ System ready for data download and parsing  

## Summary

The State Senate district reference system is now complete and ready to use. It mirrors the Congressional district system, making it easy to work with both district types using the same tools and processes. The next step is to download the actual data files from the Texas Legislature portal and run the parser to populate the reference files.
