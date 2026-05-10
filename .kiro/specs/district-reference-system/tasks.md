# Tasks: District Reference System

## Core Implementation (Done)

- [done] **1** Implement point-in-polygon algorithm
- [done] **2** Build precinct→congressional district mapping for Hidalgo County
- [done] **3** Build precinct→state house district mapping
- [done] **4** Build precinct→state senate district mapping
- [done] **5** Build precinct→commissioner district mapping
- [done] **6** Fix Commissioner Precinct 2 (CPCT2) with manual precinct list
- [done] **7** Store `old_congressional_district` for redistricting comparison
- [done] **8** Build `district_counts_cache` table
- [done] **9** Create `deploy/regenerate_all_district_caches_fast.py`

## Known Gaps to Address

- [pending] **10** Document all unmapped precincts (precincts with NULL district assignments)
- [pending] **11** Investigate VTD vintage issue: which precincts were split/renumbered after 2022?
- [pending] **12** Create manual override table for known split precincts
- [pending] **13** Add fallback: use statewide voter file precinct→VTD mapping for unmapped precincts
- [pending] **14** Verify state senate district assignments against certified election results

## Multi-County Expansion

- [pending] **15** Run district assignment for Brooks County
- [pending] **16** Run district assignment for all TX-15 counties (Cameron, Willacy, etc.)
- [pending] **17** Verify multi-county district counts match certified results

## Maintenance

- [pending] **18** Create a single "rebuild all districts" script that runs all district types in sequence
- [pending] **19** Add district assignment to the post-import pipeline (when new voter data is imported, assign districts automatically)
- [pending] **20** Add monitoring: alert if district counts deviate >5% from certified results

## Status

**Overall**: [in-progress] — core implementation done for Hidalgo County, known gaps documented, multi-county expansion pending.
