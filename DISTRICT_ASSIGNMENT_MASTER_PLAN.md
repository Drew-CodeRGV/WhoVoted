# District Assignment Master Plan

## Goal
Ensure every VUID (voter) is accurately assigned to their correct:
- Congressional District (38 districts)
- State Senate District (31 districts)  
- State House District (150 districts)
- County
- Precinct
- ZIP Code

## Data Sources (Priority Order)

### 1. County + Precinct (PRIMARY - Most Reliable)
- Source: Voter registration records
- Reliability: Highest - official voter registration data
- Coverage: Should be 100% for registered voters
- Use: Primary method for district assignment

### 2. Geocoded Address (VALIDATION)
- Source: AWS Location Service geocoding
- Reliability: High for validation
- Coverage: ~80-90% of voters with valid addresses
- Use: Validate precinct assignments, fill gaps

### 3. ZIP Code (FALLBACK)
- Source: Voter registration records
- Reliability: Lower - ZIP codes cross precinct boundaries
- Coverage: High
- Use: Approximate location when precinct unavailable

## Implementation Strategy

### Phase 1: Parse Official District Data ✓
**Status:** Files downloaded, parser ready

**Files on Server:**
- `/opt/whovoted/data/district_reference/PLANC2333_r150.xls` - Congressional counties
- `/opt/whovoted/data/district_reference/PLANC2333_r365_Prec24G.xls` - Congressional precincts
- `/opt/whovoted/data/district_reference/PLANS2168_r150.xls` - State Senate counties
- `/opt/whovoted/data/district_reference/PLANS2168_r365_*.xls` - State Senate precincts
- `/opt/whovoted/data/district_reference/PLANH2316_r150.xls` - State House counties
- `/opt/whovoted/data/district_reference/PLANH2316_r365_*.xls` - State House precincts

**Script:** `deploy/parse_district_files_fixed.py`

**Output:**
- `congressional_precincts.json` - Maps County+Precinct → Congressional District
- `state_senate_precincts.json` - Maps County+Precinct → State Senate District
- `state_house_precincts.json` - Maps County+Precinct → State House District

### Phase 2: Build Lookup System
**Script:** `deploy/build_vuid_district_lookup.py`

**Creates:**
1. `precinct_district_lookup` table in database
   - Fast O(1) lookup: (County, Precinct) → All 3 Districts
   - Indexed for performance
   - ~10,000+ precinct combinations

2. District assignment logic:
   ```sql
   UPDATE voters
   SET congressional_district = lookup.congressional_district,
       state_senate_district = lookup.state_senate_district,
       state_house_district = lookup.state_house_district
   FROM precinct_district_lookup lookup
   WHERE voters.county = lookup.county
   AND voters.precinct = lookup.precinct
   ```

### Phase 3: Validation & Quality Checks

#### Check 1: Precinct Data Completeness
```sql
SELECT 
    COUNT(*) as total_voters,
    COUNT(county) as has_county,
    COUNT(precinct) as has_precinct,
    COUNT(county) * 100.0 / COUNT(*) as county_pct,
    COUNT(precinct) * 100.0 / COUNT(*) as precinct_pct
FROM voters;
```

**Expected:** >95% should have county and precinct

#### Check 2: District Assignment Coverage
```sql
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN congressional_district IS NOT NULL THEN 1 ELSE 0 END) as has_cong,
    SUM(CASE WHEN state_senate_district IS NOT NULL THEN 1 ELSE 0 END) as has_senate,
    SUM(CASE WHEN state_house_district IS NOT NULL THEN 1 ELSE 0 END) as has_house
FROM voters;
```

**Expected:** >95% should have all 3 districts

#### Check 3: Geocode Validation
For voters with both geocoded addresses AND precinct data:
- Verify geocoded location falls within precinct boundaries
- Flag mismatches for review
- Use as quality check, not primary assignment method

```sql
SELECT 
    v.vuid,
    v.county,
    v.precinct,
    v.congressional_district,
    v.latitude,
    v.longitude
FROM voters v
WHERE v.latitude IS NOT NULL
AND v.congressional_district IS NOT NULL
-- Would need precinct boundary shapefiles for full validation
```

### Phase 4: Handle Edge Cases

#### Case 1: Voters Without Precinct Data
**Fallback Strategy:**
1. If has geocoded address → Reverse geocode to precinct
2. If has ZIP code only → Use ZIP-to-precinct approximation (less accurate)
3. If no location data → Flag for manual review

#### Case 2: Split Precincts
Some precincts are split across multiple districts. The XLS files show:
- County row with "County Total" indicator
- Multiple district rows for that county

**Handling:**
- Use most specific precinct identifier available
- May need VTD (Voting Tabulation District) for precision

#### Case 3: Address Changes
Voters who moved but haven't updated registration:
- Geocoded address may not match precinct
- **Trust precinct data** - it's the official voter registration
- Use geocode only for validation/flagging

### Phase 5: Performance Optimization

#### Cached District Counts
Create `district_counts_cache` table:
```sql
CREATE TABLE district_counts_cache (
    district_type TEXT,      -- 'congressional', 'state_senate', 'state_house'
    district_number TEXT,    -- '15', '27', etc.
    county TEXT,
    total_voters INTEGER,
    voted_2024_general INTEGER,
    voted_2024_primary INTEGER,
    first_time_voters INTEGER,
    last_updated TIMESTAMP
);
```

**Benefits:**
- Instant district counts without scanning millions of rows
- Pre-calculated for reports and dashboards
- Updated after bulk imports

#### Indexes
```sql
CREATE INDEX idx_voters_districts ON voters(congressional_district, state_senate_district, state_house_district);
CREATE INDEX idx_voters_precinct ON voters(county, precinct);
CREATE INDEX idx_voters_location ON voters(latitude, longitude) WHERE latitude IS NOT NULL;
```

## Data Quality Metrics

### Critical Metrics (Must be >95%)
- ✓ Voters with county data
- ✓ Voters with precinct data
- ✓ Voters with all 3 district assignments

### Important Metrics (Target >90%)
- Voters with geocoded addresses
- Voters with ZIP codes
- Geocode-precinct validation match rate

### Monitoring Queries
```sql
-- Daily quality check
SELECT 
    'Total Voters' as metric,
    COUNT(*) as value
FROM voters
UNION ALL
SELECT 
    'Missing Precinct' as metric,
    COUNT(*) as value
FROM voters
WHERE precinct IS NULL
UNION ALL
SELECT 
    'Missing Any District' as metric,
    COUNT(*) as value
FROM voters
WHERE congressional_district IS NULL
   OR state_senate_district IS NULL
   OR state_house_district IS NULL;
```

## Execution Plan

### Run on Server
```bash
# Connect to server
ssh -i deploy/whovoted-key.pem ubuntu@politiquera.com

# Navigate to project
cd /opt/whovoted

# Run master fix script
bash deploy/fix_all_district_assignments.sh
```

### Expected Output
```
STEP 1: Parsing district reference files...
  ✓ Parsed 38 Congressional districts
  ✓ Parsed 31 State Senate districts
  ✓ Parsed 150 State House districts
  ✓ Mapped 10,365 Congressional precincts
  ✓ Mapped 9,847 State Senate precincts
  ✓ Mapped 10,234 State House precincts

STEP 2: Building lookup system...
  ✓ Created lookup table with 12,456 entries
  ✓ Updated 1,234,567 voter records

STEP 3: Validating results...
  Congressional: 1,234,567 / 1,250,000 (98.8%)
  State Senate: 1,234,567 / 1,250,000 (98.8%)
  State House: 1,234,567 / 1,250,000 (98.8%)
  
✓ COMPLETE
```

## Post-Implementation

### 1. Verify Counts
Compare district totals against official voter registration data:
- Texas Secretary of State voter statistics
- County voter registration reports

### 2. Update Frontend
Display all 3 district types on:
- Voter detail popups
- District reports
- Campaign dashboards

### 3. API Updates
Add district filters to API endpoints:
```python
@app.route('/api/voters')
def get_voters():
    cong_district = request.args.get('congressional_district')
    senate_district = request.args.get('state_senate_district')
    house_district = request.args.get('state_house_district')
    # ... filter logic
```

### 4. Documentation
Update user documentation to explain:
- How districts are assigned
- What to do if a voter's district seems wrong
- How to report data quality issues

## Maintenance

### Regular Updates
- Re-run after bulk voter imports
- Update when redistricting occurs (every 10 years)
- Refresh cached counts daily

### Monitoring
- Set up alerts for district assignment coverage drops
- Track data quality metrics over time
- Log validation failures for review

## Success Criteria

✓ >95% of voters have all 3 district assignments
✓ District counts match official sources within 2%
✓ Geocode validation shows <5% mismatch rate
✓ Fast queries (<100ms) for district counts
✓ Zero voters with impossible district combinations

## Files Created

1. `deploy/parse_district_files_fixed.py` - Parse XLS files correctly
2. `deploy/build_vuid_district_lookup.py` - Build lookup system
3. `deploy/fix_all_district_assignments.sh` - Master execution script
4. `DISTRICT_ASSIGNMENT_MASTER_PLAN.md` - This document

## Ready to Execute

All scripts are ready. Run on server:
```bash
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com
cd /opt/whovoted
bash deploy/fix_all_district_assignments.sh
```
