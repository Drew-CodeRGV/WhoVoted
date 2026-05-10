# Tasks: McAllen ISD Bond 2026

## Data Import

- [done] **1** Import voter roster via `deploy/import_misdbond2026_roster.py`
- [done] **2** Import early voting data
- [done] **3** Import election day data via `deploy/import_misdbond2026_electionday.py`
- [done] **4** Import mail-in ballots via `deploy/import_misdbond2026_mailin.py`

## Cache Building

- [done] **5** Build voter cache: `deploy/cache_misdbond2026_voters.py`
- [done] **6** Build demographics cache: `deploy/cache_misdbond2026_demographics.py`
- [done] **7** Build report card cache: `deploy/cache_misdbond2026_reportcard.py`
- [done] **8** Build all campus report cards: `deploy/cache_misdbond2026_all_campus_reportcards.py`
- [done] **9** Build staff cache: `deploy/cache_misdbond2026_staff.py`
- [done] **10** Build student cache: `deploy/cache_misdbond2026_students.py`
- [done] **11** Build gazette cache: `deploy/cache_misdbond2026_gazette.py`
- [done] **12** Build non-voter cache: `deploy/cache_misdbond2026_nonvoters.py`

## Mini-Site

- [done] **13** Create `public/misdbond2026/index.html`
- [done] **14** Create `public/misdbond2026/map.js`
- [done] **15** Create `backend/misdbond2026_api.py` with all endpoints
- [done] **16** Register blueprint in `app.py`

## Paywall

- [in-progress] **17** Integrate `paywall.js` into `misdbond2026/map.js`
- [in-progress] **18** Server-side subscription check for `/misdbond2026/` route
- [pending] **19** Generate teaser cache file (heatmap only, no PII)
- [pending] **20** Test paywall: non-subscriber sees dots but not popup details

## Polish

- [pending] **21** Add election to `elections` table: `INSERT INTO elections (slug, name, election_date) VALUES ('misdbond2026', 'McAllen ISD Bond Election', '2026-05-10')`
- [pending] **22** Add `/misdbond2026/subscribe` route to `app.py`
- [pending] **23** Verify all cache files are current post-election

## Status

**Overall**: [in-progress] — data imported, mini-site live, paywall integration incomplete.
