# Design: MISD 2015 Bond Historical Overlay

## Approach

Import 2015 bond voter data, build cache files, add a toggle layer to the misdbond2026 map.

## Data

2015 bond voters are stored in `voter_elections` with `election_date = '2015-11-03'` (or the actual 2015 bond date). The overlay shows these voters as a separate dot layer with different styling.

## Cache Files

- `cache/misd2015_bond_overlay.json` — 2015 voter locations
- `cache/misd2015_segments.json` — precinct-level comparison data
- `cache/misd2015_advocacy_priority.json` — precincts where 2015 voters didn't return

## Frontend Integration

Add to `public/misdbond2026/map.js`:
- Toggle button: "Show 2015 Bond Voters"
- Different dot color for 2015 voters (e.g., gray vs. blue for 2026)
- Precinct comparison popup: "2015: X voters, 2026: Y voters, Change: +/-Z%"

## Files Touched

- `deploy/import_misd2015_bond.py`
- `deploy/cache_misd2015_*.py`
- `public/misdbond2026/map.js` — add overlay toggle
