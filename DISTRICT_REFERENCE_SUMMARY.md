# District Reference Data System - Summary

## What Was Created

A complete system to determine which counties, precincts, and ZIP codes belong to each Texas legislative district, independent of where we have voter data.

## The Problem We Solved

**Original Issue:** TX-15 was showing only 2 counties (Hidalgo and Brooks) because that's where we had voter data.

**Actual Answer:** TX-15 covers **11 counties** according to HB4 PlanC2333:
- 9 full counties: Bee, Brooks, DeWitt, Goliad, Gonzales, Jim Wells, Karnes, Lavaca, Live Oak
- 2 partial counties: Aransas, Hidalgo

## Files Created

### Reference Data
- `data/district_reference/congressional_districts.json` - Authoritative county list per district
- `data/district_reference/README.md` - Documentation for the reference system

### Documentation
- `FINAL_DISTRICT_REFERENCE_SOLUTION.md` - Complete solution guide
- `DISTRICT_REFERENCE_METHODOLOGY.md` - Methodology explanation
- `PLANC2333_ESSENTIAL_FILES.md` - Guide to Texas Legislature data files
- `DOWNLOAD_DISTRICT_DATA_INSTRUCTIONS.md` - Step-by-step download instructions

### Tools & Scripts
- `deploy/parse_district_files.py` - Parse Excel files from Texas Legislature
- `deploy/build_reference_from_existing_data.py` - Extract from database
- `deploy/build_reference_from_census.py` - Use Census data
- `deploy/extract_district_reference_from_shapefiles.py` - Use GIS shapefiles
- `deploy/analyze_district_coverage.py` - Analyze district coverage

### Sample Data Files
- `data/district_reference/planc2333_r150.xls` - Counties by district
- `data/district_reference/planc2333_r365_prec24g.xls` - Precincts by district
- `data/district_reference/planc2333_r385.xls` - ZIP codes by district
- `data/district_reference/planc2333_r155.xls` - Split counties
- `data/district_reference/planc2333_r202.xls` - Population and voter data

## How to Use

### Immediate Use
The `congressional_districts.json` file already has TX-15 data:
```json
{
  "15": {
    "counties": ["Aransas", "Bee", "Brooks", "DeWitt", "Goliad", 
                 "Gonzales", "Hidalgo", "Jim Wells", "Karnes", 
                 "Lavaca", "Live Oak"],
    "total_counties": 11
  }
}
```

### Get Complete Data for All 38 Districts
1. Go to https://data.capitol.texas.gov/dataset/planc2333
2. Download the XLS files (or use the ones already in the repo)
3. Run: `python deploy/parse_district_files.py`
4. This populates all 38 districts with complete data

### In Campaign Reports
```python
# Load reference
with open('data/district_reference/congressional_districts.json') as f:
    districts = json.load(f)

# Show coverage
district_info = districts['15']
actual_counties = query_database_for_counties('15')

print(f"District covers: {district_info['total_counties']} counties")
print(f"We have data for: {len(actual_counties)} counties")
print(f"Coverage: {len(actual_counties)/district_info['total_counties']*100:.1f}%")
```

## Key Insights

1. **Authoritative Source:** Texas Legislature redistricting data is the official source
2. **Data vs Reality:** Voter data availability ≠ district boundaries
3. **Three-Tier Approach:** Manual → Automated → GIS (choose based on needs)
4. **Extensible:** Same methodology works for State Senate and State House

## Data Sources

### Congressional Districts (38 districts)
- **Portal:** https://data.capitol.texas.gov/dataset/planc2333
- **Plan:** PLANC2333 (HB4, 89th Legislature, 2nd C.S., 2025)

### State Senate (31 districts)
- **Portal:** https://data.capitol.texas.gov/dataset/plans2168
- **Plan:** PLANS2168 (SB4, 2025)

### State House (150 districts)
- **Portal:** https://data.capitol.texas.gov/dataset/planh2316
- **Plan:** PLANH2316 (HB1, 2025)

## Next Steps

1. **Populate remaining districts:** Run parser on downloaded files
2. **Add to reports:** Update campaign reports to show coverage metrics
3. **Extend to State districts:** Apply same methodology to Senate/House
4. **Add precincts:** Parse precinct data for precinct-level coverage

## Files Synced to GitHub

All documentation, scripts, and reference data are now in the repository:
- ✓ Reference JSON files
- ✓ Complete documentation
- ✓ Parser scripts
- ✓ Sample XLS files
- ✓ Methodology guides

## The Bottom Line

**TX-15 has 11 counties, not 2.**

The system now knows this and can show campaigns:
- "District covers 11 counties"
- "We have data for 2 counties (18% coverage)"
- "Missing data for: Aransas, Bee, DeWitt, Goliad, Gonzales, Jim Wells, Karnes, Lavaca, Live Oak"

This gives campaigns a clear picture of what they're working with and what they're missing.
