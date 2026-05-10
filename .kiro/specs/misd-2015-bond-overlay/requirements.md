# Spec: MISD 2015 Bond Historical Overlay

## Problem

McAllen ISD passed a bond in 2015. Comparing 2015 bond voter turnout with the 2026 bond election provides valuable context: which precincts increased/decreased participation, which demographics shifted.

## Users

- Campaign operatives analyzing bond election patterns
- Subscribers to the misdbond2026 election site

## Acceptance Criteria

1. Historical 2015 bond data is imported into the DB.
2. A "2015 Bond Overlay" toggle on the misdbond2026 map shows 2015 voter dots alongside 2026.
3. Precinct-level comparison: 2015 vs 2026 turnout per precinct.
4. Advocacy priority segments: precincts where 2015 voters didn't return in 2026.

## Current State

- `deploy/import_misd2015_bond.py` — data importer (exists)
- `deploy/cache_misd2015_bond_overlay.py` — overlay cache builder (exists)
- `deploy/cache_misd2015_segments.py` — segment cache builder (exists)
- `deploy/cache_misd2015_advocacy_priority.py` — advocacy priority cache (exists)
- Integration into misdbond2026 map: not yet done

## Out of Scope

- Full 2015 election mini-site (just an overlay on the 2026 site)
