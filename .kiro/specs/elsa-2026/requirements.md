# Spec: Elsa 2026 Election Site

## Problem

The City of Elsa held a municipal election in 2026. The platform needs a dedicated election mini-site at `/elsa2026/` following the same pattern as `misdbond2026/`.

## Users

- Elsa campaign operatives
- Subscribers who purchased access to this election

## Acceptance Criteria

1. `/elsa2026/` serves the election mini-site with voter map.
2. Voter dots show all voters who cast ballots in the Elsa 2026 election.
3. Report card shows demographics and precinct performance.
4. Gazette shows data-driven stories.
5. Non-subscribers see teaser view; subscribers see full view.
6. Cache files are pre-built and served statically.
7. Election is registered in `elections` table with slug `elsa2026`.

## Current State

- Mini-site exists at `public/elsa2026/`
- Cache builders exist: `deploy/cache_elsa2026_*.py`
- Data imported
- Paywall integration: partially implemented

## Out of Scope

- Historical Elsa election data (only 2026)
