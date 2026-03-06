# Complete Guide: Texas District Reference Data System

## Overview

This system provides authoritative reference data for all Texas legislative districts:
- **Congressional Districts**: 38 districts (PLANC2333)
- **State Senate Districts**: 31 districts (PLANS2168)
- **State House Districts**: 150 districts (PLANH2316) - Future

The key insight: District boundaries are defined by redistricting legislation, NOT by where we have voter data.

## File Structure

```
WhoVoted/data/district_reference/
├── congressional_districts.json       # Main reference (TX-15 verified)
├── state_senate_districts.json        # Main reference (all 31 districts)
├── congressional_counties.json        # Parsed from PLANC2333_r150.xls
├── congressional_precincts.json       # Parsed from PLANC2333_r365.xls
├── state_senate_counties.json         # Parsed from PLANS2168_r150.xls
├── state_senate_precincts.json        # Parsed from PLANS2168_r365.xls
└── [downloaded XLS files]             # Source data from Texas Legislature
```

## Quick Start

### 1. Congressional Districts (38 districts)

**Data Source:** https://data.capitol.texas.gov/dataset/planc2333

**Download these files:**
- PLANC2333_r150.xls (Districts by County)
- PLANC2333_r365_Prec24G.xls (Precincts by District)
- PLANC2333_r202_22G-24G.xls (Voter Data)
- PLANC2333_r385.xls (ZIP Codes)

**Parse the data:**
```bash
python deploy/parse_district_files.py
```

**Result:** Creates `congressional_counties.json` and `congressional_precincts.json`

### 2. State Senate Districts (31 districts)

**Data Source:** https://data.capitol.texas.gov/dataset/plans2168

**Download these files:**
- PLANS2168_r150.xls (Districts by County)
- PLANS2168_r365_Prec2024 General.xls (Precincts by District)
- PLANS2168_r202_22G-24G.xls (Voter Data)
- PLANS2168_r385_2024.xls (ZIP Codes)

**Parse the data:**
```bash
python deploy/parse_district_files.py
```

**Result:** Creates `state_senate_counties.json` and `state_senate_precincts.json`

## Example: TX-15 Congressional District

From `congressional_districts.json`:

```json
{
  "15": {
    "counties": [
      "Aransas", "Bee", "Brooks", "DeWitt", "Goliad", 
      "Gonzales", "Hidalgo", "Jim Wells", "Karnes", 
      "Lavaca", "Live Oak"
    ],
    "split_counties": ["Aransas", "Hidalgo"],
    "total_counties": 11,
    "source": "HB4 PlanC2333",
    "verified": true,
    "notes": "9 full counties + 2 partial counties"
  }
}
```

**Key Facts:**
- TX-15 has 11 counties (not 2!)
- We only have voter data for 2 counties (Hidalgo, Brooks)
- This means we have 18% county coverage, not 100%

## How to Use in Reports

### Show District Coverage

```python
import json

# Load reference data
with open('data/district_reference/congressional_districts.json') as f:
    DISTRICT_REF = json.load(f)

def get_district_coverage(district_num):
    """Calculate what % of district we have data for."""
    
    # What SHOULD be in the district
    reference = DISTRICT_REF.get(str(district_num), {})
    total_counties = reference.get('total_counties', 0)
    all_counties = reference.get('counties', [])
    
    # What we HAVE data for
    data_counties = query_database_for_counties(district_num)
    
    return {
        'district': f'TX-{district_num}',
        'total_counties': total_counties,
        'counties_with_data': len(data_counties),
        'coverage_pct': len(data_counties) / total_counties * 100 if total_counties > 0 else 0,
        'missing_counties': [c for c in all_counties if c not in data_counties]
    }

# Example output for TX-15:
# {
#   'district': 'TX-15',
#   'total_counties': 11,
#   'counties_with_data': 2,
#   'coverage_pct': 18.2,
#   'missing_counties': ['Aransas', 'Bee', 'DeWitt', 'Goliad', 'Gonzales', 
#                        'Jim Wells', 'Karnes', 'Lavaca', 'Live Oak']
# }
```

### Show in Campaign Reports

```python
def generate_district_report_card(district_num):
    """Generate comprehensive district report."""
    
    coverage = get_district_coverage(district_num)
    
    return {
        'district_info': {
            'name': coverage['district'],
            'total_counties': coverage['total_counties'],
            'data_coverage': f"{coverage['coverage_pct']:.1f}%"
        },
        'data_quality': {
            'counties_with_data': coverage['counties_with_data'],
            'counties_missing': len(coverage['missing_counties']),
            'status': 'Partial' if coverage['coverage_pct'] < 100 else 'Complete'
        },
        'missing_data': coverage['missing_counties']
    }
```

## Parser Script Details

The `deploy/parse_district_files.py` script:

1. **Reads Excel files** from Texas Legislature data portals
2. **Extracts district-county relationships** from r150 files
3. **Extracts district-precinct relationships** from r365 files
4. **Handles both Congressional and State Senate** districts
5. **Creates JSON output files** for easy integration

**Features:**
- Automatic column detection (handles different Excel formats)
- Error handling for malformed data
- Support for multiple file naming patterns
- Comprehensive summary output

## Data Portal Files

### Priority 1 Files (Download First)

| File | Purpose | Congressional | State Senate |
|------|---------|--------------|--------------|
| r150 | Counties per district | PLANC2333_r150.xls | PLANS2168_r150.xls |
| r365 | Precincts per district | PLANC2333_r365_Prec24G.xls | PLANS2168_r365_Prec2024 General.xls |
| r202 | Voter registration data | PLANC2333_r202_22G-24G.xls | PLANS2168_r202_22G-24G.xls |
| r385 | ZIP codes per district | PLANC2333_r385.xls | PLANS2168_r385_2024.xls |
| r155 | Split counties | PLANC2333_r155.xls | PLANS2168_r155.xls |

### Bulk Download Options

**Congressional:** PLANC2333_All_Files_20251009.zip (~500MB)
**State Senate:** PLANS2168_All_Files_20250220.zip

## Documentation Files

- `PLANC2333_ESSENTIAL_FILES.md` - Complete guide to Congressional district files
- `PLANS2168_ESSENTIAL_FILES.md` - Complete guide to State Senate district files
- `FINAL_DISTRICT_REFERENCE_SOLUTION.md` - Original solution documentation
- `DISTRICT_REFERENCE_METHODOLOGY.md` - Methodology and approach

## Integration Points

### 1. Campaign Reports Module

Update `backend/reports.py` to use reference data:

```python
from pathlib import Path
import json

# Load at module level
DISTRICT_REF_DIR = Path(__file__).parent.parent / 'data' / 'district_reference'

with open(DISTRICT_REF_DIR / 'congressional_districts.json') as f:
    CONGRESSIONAL_REF = json.load(f)

with open(DISTRICT_REF_DIR / 'state_senate_districts.json') as f:
    STATE_SENATE_REF = json.load(f)
```

### 2. Frontend Display

Show coverage metrics in dashboard:

```javascript
// In dashboard.js
function displayDistrictCoverage(districtData) {
    const coverage = districtData.coverage_pct;
    const status = coverage === 100 ? 'Complete' : 'Partial';
    const color = coverage === 100 ? 'green' : 'orange';
    
    return `
        <div class="district-coverage">
            <h3>District Coverage</h3>
            <div class="coverage-bar" style="background: ${color}">
                ${coverage.toFixed(1)}%
            </div>
            <p>${districtData.counties_with_data} of ${districtData.total_counties} counties</p>
            <span class="status ${status.toLowerCase()}">${status}</span>
        </div>
    `;
}
```

### 3. Data Validation

Validate uploads against reference data:

```python
def validate_upload(file_data, district_num):
    """Validate uploaded data against district reference."""
    
    reference = CONGRESSIONAL_REF.get(str(district_num), {})
    expected_counties = set(reference.get('counties', []))
    
    uploaded_counties = set(file_data['county'].unique())
    
    # Check for invalid counties
    invalid = uploaded_counties - expected_counties
    if invalid:
        return {
            'valid': False,
            'error': f'Invalid counties for TX-{district_num}: {invalid}',
            'expected': list(expected_counties)
        }
    
    return {'valid': True}
```

## Future Enhancements

### 1. State House Districts (150 districts)

**Data Source:** https://data.capitol.texas.gov/dataset/planh2316

Same process as Congressional and Senate:
1. Download PLANH2316_r150.xls and PLANH2316_r365.xls
2. Run parser script (already supports it)
3. Creates `state_house_counties.json` and `state_house_precincts.json`

### 2. Automated Updates

Create a script to check for new redistricting data:

```python
def check_for_updates():
    """Check Texas Legislature portals for new data."""
    portals = [
        'https://data.capitol.texas.gov/dataset/planc2333',
        'https://data.capitol.texas.gov/dataset/plans2168',
        'https://data.capitol.texas.gov/dataset/planh2316'
    ]
    # Check last-modified dates, download if newer
```

### 3. GIS Integration

Use shapefiles for precise address-to-district lookup:

```python
import geopandas as gpd

def get_district_from_coordinates(lat, lon):
    """Determine district from GPS coordinates."""
    districts = gpd.read_file('data/district_reference/PLANC2333.zip')
    point = gpd.GeoSeries([Point(lon, lat)], crs='EPSG:4326')
    result = gpd.sjoin(point, districts, how='left', predicate='within')
    return result['DISTRICT'].iloc[0]
```

## Key Principles

1. **District boundaries ≠ Data availability**
   - Districts are defined by legislation
   - We may not have data for all counties in a district
   - Always show both: what SHOULD be there vs what we HAVE

2. **Authoritative sources**
   - Texas Legislature redistricting portals are the source of truth
   - Don't rely on database queries to determine district composition
   - Reference files are the authority

3. **Three-tier approach**
   - Tier 1: Manual JSON files (immediate, verified data)
   - Tier 2: Parsed Excel files (automated, complete data)
   - Tier 3: GIS shapefiles (precise, spatial data)

4. **Transparency**
   - Always show users what % of district we have data for
   - List missing counties/precincts
   - Don't claim completeness when we have partial data

## Troubleshooting

### Parser fails to read Excel file

Try installing both Excel engines:
```bash
pip install xlrd openpyxl
```

### Column names don't match

The parser auto-detects columns by looking for keywords like "district", "county", "precinct". If it fails, check the Excel file structure and update the parser logic.

### Missing districts in output

Check that:
1. Excel file is the correct version (r150 for counties, r365 for precincts)
2. File isn't corrupted (try re-downloading)
3. Parser completed without errors (check console output)

## Summary

This system provides a complete, authoritative reference for Texas legislative districts. It separates "what should be in the district" (from redistricting legislation) from "what data we have" (from voter files), enabling accurate coverage reporting and data validation.

**Next Steps:**
1. Download Congressional district files (PLANC2333)
2. Download State Senate district files (PLANS2168)
3. Run parser script
4. Integrate reference data into reports module
5. Update frontend to show coverage metrics
