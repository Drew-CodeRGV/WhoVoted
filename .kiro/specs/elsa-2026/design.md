# Design: Elsa 2026 Election Site

## Architecture

Follows the standard election mini-site pattern. Same structure as `misdbond2026/`.

## Frontend

- `public/elsa2026/index.html` — main page
- `public/elsa2026/map.js` — map logic + paywall integration

## Backend

Uses the main `app.py` endpoints with election-specific query parameters. No separate Blueprint needed (unlike misdbond2026 which has a dedicated API).

## Cache Files

Built by `deploy/cache_elsa2026_*.py` scripts:
- `cache_elsa2026_voters.py` — voter locations
- `cache_elsa2026_demographics.py` — demographic breakdown
- `cache_elsa2026_gazette.py` — gazette stories
- `cache_elsa2026_nonvoters.py` — non-voter overlay
- `cache_elsa2026_opportunity.py` — opportunity overlay
- `cache_elsa2026_reportcard.py` — report card data

Refresh: `deploy/refresh_elsa_caches.py`

## Paywall

Same pattern as misdbond2026: `window.__subscribed` flag, `paywall.js` integration.

## Files Touched

- `public/elsa2026/index.html`
- `public/elsa2026/map.js`
- `deploy/cache_elsa2026_*.py`
- `deploy/refresh_elsa_caches.py`
