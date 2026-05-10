# Spec: Politiquera Gazette

## Problem

Raw voter data is hard to interpret without context. The Gazette is a newspaper-style panel that generates data-driven stories from the voter database — turnout narratives, demographic breakdowns, party shift analysis — presented as readable articles rather than raw numbers.

## Users

- Subscribers who want analysis, not just data
- Journalists looking for story angles
- Campaign staff who want shareable insights

## Acceptance Criteria

1. Gazette panel opens as a slide-in panel on each election mini-site.
2. Each gazette contains 4–8 data-driven "stories" generated from the election's cache data.
3. Stories include: turnout summary, party breakdown, demographic analysis, precinct performance, notable shifts.
4. Stories are pre-generated and cached (not generated on-demand from the DB).
5. Gazette is paywalled — non-subscribers see blurred content with "Subscribe to view."
6. Gazette content is readable on mobile.
7. Each story has a headline, lede, and 2–3 paragraphs of data-driven narrative.
8. Stories reference specific numbers from the DB (not generic templates).

## Story Types

- **Turnout Summary**: "X voters cast ballots in [election], representing Y% of registered voters."
- **Party Breakdown**: "Democrats outnumbered Republicans Z:1 in early voting."
- **Demographic Analysis**: Age/gender breakdown of who voted.
- **Precinct Performance**: Top and bottom precincts by turnout.
- **New Voters**: First-time voters as a share of total.
- **Voting Method**: Early vs. election day vs. mail-in split.
- **Geographic Story**: Which neighborhoods had highest/lowest turnout.

## Current State

- `public/newspaper.js` — gazette panel UI (implemented)
- `deploy/generate_statewide_gazette_cache.py` — statewide gazette cache builder
- `deploy/cache_misdbond2026_gazette.py` — MISD bond gazette cache
- `deploy/cache_elsa2026_gazette.py` — Elsa 2026 gazette cache
- Gazette is live on misdbond2026 and elsa2026 mini-sites
- Paywall integration: partially implemented

## Out of Scope

- AI-generated narrative (current implementation uses templates + data substitution)
- Social media sharing of individual stories
- Email newsletter export
