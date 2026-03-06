# Final Solution: District Reference Data

## The Problem

The system needs to know how many counties, precincts, and ZIP codes are in each Texas Congressional District (and eventually State Senate and State House districts) to:

1. Show accurate "District Coverage" metrics
2. Display "X counties with data, Y counties missing data"
3. Generate proper campaign report cards
4. Validate data completeness

## The Answer: TX-15 Has 11 Counties

Based on HB4 PlanC2333 (89th Legislature, 2nd C.S., 2025):

**TX-15 includes 11 counties:**
- 9 full counties: Bee, Brooks, DeWitt, Goliad, Gonzales, Jim Wells, Karnes, Lavaca, Live Oak
- 2 partial counties: Aransas, Hidalgo

## Three-Tier Solution

### Tier 1: Manual Reference File (IMMEDIATE)

Create a JSON file with the authoritative data for the districts you care about most.

**File:** `WhoVoted/data/district_reference/congressional_districts.json`

```json
{
  "15": {
    "counties": ["Aransas", "Bee", "Brooks", "DeWitt", "Goliad", "Gonzales", "Hidalgo", "Jim Wells", "Karnes", "Lavaca", "Live Oak"],
    "split_counties": ["Aransas", "Hidalgo"],
    "total_counties": 11,
    "source": "HB4 PlanC2333",
    "verified": true
  },
  "28": {
    "counties": [],
    "total_counties": 0,
    "source": "pending",
    "verified": false
  },
  "34": {
    "counties": [],
    "total_counties": 0,
    "source": "pending",
    "verified": false
  }
}
```

**How to populate:**
1. Go to https://data.capitol.texas.gov/dataset/planc2333
2. Download PLANC2333_r150.pdf (Districts by County)
3. For each district, manually list the counties
4. Update the JSON file

### Tier 2: Automated Extraction (RECOMMENDED)

Download the Excel files and run the parser:

**Steps:**
1. Download from https://data.capitol.texas.gov/dataset/planc2333:
   - `PLANC2333_r150.xls` → Save to `WhoVoted/data/district_reference/`
   - `PLANC2333_r365_Prec24G.xls` → Save to `WhoVoted/data/district_reference/`
   
2. Run: `python deploy/parse_district_files.py`

3. This creates:
   - `district_counties.json` - All 38 districts with counties
   - `district_precincts.json` - All 38 districts with precincts by county

### Tier 3: GIS/Shapefile Analysis (COMPLETE)

For full automation, use shapefiles:

**Steps:**
1. Download shapefiles from https://data.capitol.texas.gov/dataset/planc2333
2. Use GeoPandas to spatially join with county/precinct boundaries
3. Extract relationships programmatically

**Script:** `deploy/extract_district_reference_from_shapefiles.py`

## Implementation in Reports

Once you have the reference files, update the reports module:

```python
# Load reference data
with open('data/district_reference/congressional_districts.json') as f:
    DISTRICT_REFERENCE = json.load(f)

def generate_district_report(district_num):
    # Get what SHOULD be in the district
    reference = DISTRICT_REFERENCE.get(district_num, {})
    total_counties = reference.get('total_counties', 0)
    all_counties = reference.get('counties', [])
    
    # Get what we HAVE data for
    data_counties = query_database_for_counties(district_num)
    
    # Show both
    return {
        'district_coverage': {
            'total_counties': total_counties,
            'counties_with_data': len(data_counties),
            'data_coverage_pct': len(data_counties) / total_counties * 100 if total_counties > 0 else 0
        },
        'counties': [
            {
                'name': county,
                'has_data': county in data_counties,
                'voter_count': data_counties.get(county, 0)
            }
            for county in all_counties
        ]
    }
```

## For State Senate and State House

The same methodology applies:

**State Senate (31 districts):**
- Data source: https://data.capitol.texas.gov/dataset/plans2168
- Files: PLANS2168_r150.xls (counties), PLANS2168_r365.xls (precincts)

**State House (150 districts):**
- Data source: https://data.capitol.texas.gov/dataset/planh2316
- Files: PLANH2316_r150.xls (counties), PLANH2316_r365.xls (precincts)

## Quick Start: Just TX-15

If you only need TX-15 right now, I've already documented it:

```json
{
  "15": {
    "counties": [
      "Aransas",
      "Bee", 
      "Brooks",
      "DeWitt",
      "Goliad",
      "Gonzales",
      "Hidalgo",
      "Jim Wells",
      "Karnes",
      "Lavaca",
      "Live Oak"
    ],
    "split_counties": ["Aransas", "Hidalgo"],
    "total_counties": 11
  }
}
```

Use this in your reports immediately while you work on getting the complete data for all 38 districts.

## Scripts Created

1. `deploy/parse_district_files.py` - Parses downloaded Excel files
2. `deploy/build_reference_from_existing_data.py` - Extracts from your database
3. `deploy/build_reference_from_census.py` - Uses Census TIGER data
4. `deploy/extract_district_reference_from_shapefiles.py` - Uses GIS shapefiles

## Recommendation

**For immediate use:** Create the manual JSON file with TX-15, TX-28, TX-34 data

**For complete solution:** Download the Excel files and run the parser (Tier 2)

This gives you authoritative data for all 38 congressional districts without needing to manually count from PDFs or wrestle with shapefiles.
