# First-Time Voter Logic - Current Implementation

## Overview
The system uses **multiple different methods** to identify first-time voters, which may be causing inconsistencies.

## Current Logic Locations

### 1. Flag Setting During Data Processing
**Files:** `database.py:780`, `processor.py:1616`

**Logic:**
```python
has_prior = _county_has_prior_data(conn, county, election_date)
is_new_voter = (vuid not in prior_vuids) if has_prior else False
```

**What it does:**
- Checks if voter's VUID appears in ANY prior election
- Only flags if county has prior election data
- Simple binary: has prior history = not new, no prior history = new

**Helper function:**
```python
def _county_has_prior_data(conn, county, election_date):
    """Returns True if county has ANY voter_elections records before election_date"""
    # Checks for at least 1 record with party_voted before this election
```

### 2. Stats Calculation in database.py
**File:** `database.py:1113-1130`

**Logic:**
```sql
SELECT COUNT(*) FROM _stats_vuids t
WHERE NOT EXISTS (
    SELECT 1 FROM voter_elections ve_old
    WHERE ve_old.vuid = t.vuid
      AND ve_old.election_date < ?
      AND ve_old.party_voted != '' AND ve_old.party_voted IS NOT NULL
)
```

Then zeros out if `!_county_has_prior_data()`

**What it does:**
- Same as flag logic: no prior voting history = new
- But then applies county-level check

### 3. API Endpoint Calculations
**Files:** `app.py:1237-1320`, `reports.py:428-510`

**Logic:**
```python
prior_election_count = COUNT(DISTINCT election_date WHERE date < current)

if prior_election_count >= 3:
    # Full logic: 18-19 year olds OR no prior history
    new_voters = voters WHERE (
        birth_year BETWEEN (election_year - 19) AND (election_year - 18)
        OR NOT EXISTS (prior election with party_voted)
    )
else:
    # Restricted logic: only 18-19 year olds
    new_voters = voters WHERE birth_year BETWEEN (election_year - 19) AND (election_year - 18)
```

**What it does:**
- **Different logic** than the flag!
- Adds age-based detection (18-19 year olds)
- Only uses "no prior history" if we have 3+ elections in DB
- More conservative approach

## The Problem

### Inconsistency Between Methods

**Example scenario:**
- Voter is 25 years old
- Has never voted in a primary before
- County has prior election data

**What happens:**
1. **Flag logic** (database.py): `is_new_voter = True` ✓
2. **Stats logic** (database.py): `new_voters++` ✓
3. **API logic** (app.py/reports.py): 
   - If <3 prior elections: NOT counted (age > 19) ✗
   - If 3+ prior elections: Counted (no prior history) ✓

### County-Level Check Issues

The `_county_has_prior_data()` function checks if a county has ANY prior data. This can cause issues:

- **Statewide data import**: If we import statewide EVR data, every county suddenly "has prior data"
- **Partial imports**: If only some counties were imported for prior elections, others get zeroed out
- **False negatives**: A county might have data for 2024 but not 2022, making 2022 voters look "new" in 2026

## What Should Be Fixed

### Option 1: Standardize on Simple Logic (Recommended)
Use the same logic everywhere:
```
is_new_voter = voter has NO prior primary voting history (any party, any election)
```

Remove:
- Age-based detection (18-19 year olds)
- County-level prior data checks
- 3+ election threshold

**Pros:**
- Simple, consistent
- Easy to understand and verify
- Works regardless of data completeness

**Cons:**
- May overcount in counties with incomplete historical data

### Option 2: Standardize on Complex Logic
Use the API logic everywhere (18-19 OR no prior if 3+ elections):

**Pros:**
- More conservative
- Handles incomplete data better

**Cons:**
- Complex to maintain
- Flag needs to be recalculated when new elections are added
- Inconsistent across time periods

### Option 3: Add Data Quality Flags
Keep current logic but add metadata:
- Track which counties have complete historical data
- Show confidence levels in UI
- Allow filtering by data quality

## Recommended Action

1. **Run audit script** to see actual numbers:
   ```bash
   python3 /opt/whovoted/deploy/audit_first_time_voter_logic.py
   ```

2. **Decide on single logic** to use everywhere

3. **Update all locations** to use same logic:
   - `database.py` (flag setting)
   - `database.py` (stats calculation)
   - `app.py` (API endpoints)
   - `reports.py` (report generation)
   - `processor.py` (CSV import)

4. **Regenerate all cached data** with consistent logic

5. **Add tests** to prevent future divergence
