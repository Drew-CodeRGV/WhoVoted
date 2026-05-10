# Spec: McAllen ISD Bond 2026

## Problem

McAllen ISD held a bond election on May 10, 2026. The platform needs a dedicated election mini-site at `/misdbond2026/` with voter map, report cards, gazette, and demographic overlays specific to the MISD bond district (McAllen zip codes: 78501–78505).

## Users

- Campaign operatives tracking bond support
- Journalists covering the election
- Subscribers who purchased access to this election

## Acceptance Criteria

1. `/misdbond2026/` serves the election mini-site with voter map.
2. Voter dots show all voters who cast ballots in the May 10, 2026 election within McAllen zip codes.
3. Report card shows: campus-level data, district demographics, staff overlay, student enrollment.
4. Gazette shows data-driven stories about the election.
5. Non-subscribers see teaser view (dots visible, popups/report card/gazette paywalled).
6. Subscribers see full view including voter names, party, voting method.
7. Cache files are pre-built and served statically for performance.
8. Election date in DB: `2026-05-10`.
9. MISD boundary is defined by zip codes (78501–78505), not a GeoJSON polygon.

## Data Sources

- Voter rolls: imported via `deploy/import_misdbond2026_roster.py`
- Election day results: `deploy/import_misdbond2026_electionday.py`
- Mail-in ballots: `deploy/import_misdbond2026_mailin.py`
- Campus report cards: scraped via `deploy/cache_misdbond2026_all_campus_reportcards.py`
- Staff data: `deploy/cache_misdbond2026_staff.py`
- Student enrollment: `deploy/cache_misdbond2026_students.py`

## Current State

- Mini-site exists at `public/misdbond2026/`
- Backend API at `backend/misdbond2026_api.py`
- Cache builders exist in `deploy/`
- Paywall integration: partially implemented (see `deploy/fix_misdbond_paywall.py`)
- Election data imported for early voting and election day

## Out of Scope

- Precinct-level boundary GeoJSON for MISD (zip-code boundary is sufficient)
- Absentee/provisional ballot tracking
