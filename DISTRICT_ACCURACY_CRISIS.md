# District Accuracy Crisis - CRITICAL FIX REQUIRED

## Problem Statement

TX-15 Congressional District report shows Travis County voters, which is IMPOSSIBLE.
- TX-15 is in South Texas (Hidalgo, Starr, Brooks, Jim Hogg, Willacy, Kenedy)
- Travis County is in Central Texas (Austin area) - in TX-21, TX-25, TX-35, TX-37
- This indicates systematic district assignment errors across the database

## Impact

- Campaign reports show completely wrong numbers
- Voter counts are inflated/deflated incorrectly
- Geographic targeting is broken
- Data integrity is compromised for ALL districts

## Root Cause Analysis

The district assignment logic is either:
1. Using incorrect precinct-to-district mappings
2. Using outdated district boundaries (pre-2023 redistricting)
3. Assigning districts based on county alone (wrong - districts cross county lines)
4. Point-in-polygon checks failing due to coordinate/projection issues

## Fix Strategy - Multi-Phase Approach

### Phase 1: DIAGNOSE (Immediate)
Identify the scope and source of the problem

### Phase 2: ACQUIRE TRUTH (Day 1)
Get authoritative district boundary data

### Phase 3: VALIDATE (Day 1-2)
Build verification tools to check assignments

### Phase 4: REBUILD (Day 2-3)
Regenerate all district assignments from scratch

### Phase 5: VERIFY (Day 3)
Confirm accuracy before deploying

### Phase 6: PREVENT (Ongoing)
Add validation to prevent future errors

## Execution Plan

See individual step files:
- `verify_districts_step1_diagnose.py` - Identify all wrong assignments
- `verify_districts_step2_acquire.py` - Download official boundaries
- `verify_districts_step3_validate.py` - Build validation tools
- `verify_districts_step4_rebuild.py` - Regenerate assignments
- `verify_districts_step5_verify.py` - Confirm accuracy
- `verify_districts_step6_prevent.py` - Add safeguards

## Priority

🔴 CRITICAL - Block all campaign report usage until fixed
