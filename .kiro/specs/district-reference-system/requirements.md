# Spec: District Reference System

## Problem

Assigning voters to legislative districts (congressional, state house, state senate, commissioner) requires accurate precinct→district mapping. The initial approach used coordinate comparisons, which produced wrong counts. The current approach uses point-in-polygon on precinct centroids, which is accurate but has known gaps.

## Users

- Platform: needs correct district assignments in `voters` table
- Campaign staff: need accurate district-level voter counts
- Researchers: need to trust the district data

## Acceptance Criteria

1. Every voter in the DB has correct values for: `congressional_district`, `state_house_district`, `state_senate_district`, `commissioner_district`.
2. District assignment uses point-in-polygon on precinct centroids (not coordinate comparisons).
3. District boundaries are stored as GeoJSON in `/opt/whovoted/public/data/districts.json`.
4. The `district_counts_cache` table is populated and accurate.
5. Known accuracy gaps are documented (VTD vintage, split precincts).
6. A rebuild script exists to regenerate all district assignments from scratch.

## Known Accuracy Gaps

1. **VTD vintage**: Boundary files are from the 2020 redistricting cycle. Precincts renumbered or split after 2022 may map incorrectly.
2. **Unmapped precincts**: Some precincts have no geocoded voters, so their centroid can't be calculated. These voters have NULL district assignments.
3. **Commissioner Precinct 2 (CPCT2)**: Had a known discrepancy that required manual precinct list correction. The fix is in `deploy/fix_cpct2_with_correct_precincts.py`.
4. **TX-15 boundary**: The congressional district boundary changed in 2022 redistricting. The old boundary is stored as `old_congressional_district` for comparison.

## Current State

- Point-in-polygon methodology implemented and working
- District assignments populated for Hidalgo County
- State house and senate districts implemented
- Commissioner districts implemented (with CPCT2 fix)
- TX-15 congressional district implemented
- Known gaps documented above

## Out of Scope

- Real-time district lookup for new voter registrations (batch process is sufficient)
- Multi-state district support
