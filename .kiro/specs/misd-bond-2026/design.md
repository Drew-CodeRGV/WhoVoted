# Design: McAllen ISD Bond 2026

## Architecture

Follows the standard election mini-site pattern established by `elsa2026/`. The MISD bond site is unique in that its boundary is defined by zip codes rather than a GeoJSON polygon.

## Backend

### `backend/misdbond2026_api.py`
Dedicated Blueprint for MISD bond endpoints. Registered in `app.py`.

Key endpoints:
- `GET /api/misdbond2026/stats` — total voters, precinct breakdown
- `GET /api/misdbond2026/voters` — individual voter locations (subscription-gated)
- `GET /api/misdbond2026/reportcard` — district-level report card
- `GET /api/misdbond2026/campus/<campus_id>` — campus-level report card
- `GET /api/misdbond2026/gazette` — data-driven stories
- `GET /api/misdbond2026/demographics` — demographic overlays
- `GET /api/misdbond2026/nonvoters` — non-voter overlay
- `GET /api/misdbond2026/students` — student enrollment overlay
- `GET /api/misdbond2026/staff` — staff overlay

### Boundary Definition

```python
MCALLEN_ZIPS = ('78501', '78502', '78503', '78504', '78505')
# All queries filter: WHERE v.zip IN (?, ?, ?, ?, ?)
```

### Election Date

```python
ELECTION_DATE = '2026-05-10'
```

## Cache Strategy

Pre-built JSON files in `/opt/whovoted/public/cache/misdbond2026/`:
- `voters.json` — full voter data (subscription-gated, served via API not static)
- `teaser.json` — aggregated heatmap only (public)
- `reportcard.json` — district report card
- `campus_<id>.json` — per-campus report cards
- `gazette.json` — gazette stories
- `demographics.json` — demographic breakdown
- `nonvoters.json` — non-voter list
- `students.json` — student enrollment
- `staff.json` — staff data

Cache is rebuilt by `deploy/refresh_misdbond2026_all.py`.

## Paywall Integration

The mini-site uses `public/paywall.js`. The server injects:
```javascript
window.__subscribed = true|false;
window.__electionSlug = 'misdbond2026';
```

Non-subscribers see:
- Voter dots (heatmap from `teaser.json`)
- Blurred popups with "Subscribe to view voter details"
- Blurred report card with "Subscribe to view"
- Blurred gazette with "Subscribe to view"

## Frontend

- `public/misdbond2026/index.html` — main page
- `public/misdbond2026/map.js` — map logic, paywall integration
- Shared: `public/paywall.js`, `public/newspaper.js`

## Files Touched

- `backend/misdbond2026_api.py` — API endpoints
- `backend/app.py` — register blueprint
- `public/misdbond2026/index.html` — mini-site HTML
- `public/misdbond2026/map.js` — map + paywall logic
- `deploy/cache_misdbond2026_*.py` — cache builders
- `deploy/refresh_misdbond2026_all.py` — full refresh script
