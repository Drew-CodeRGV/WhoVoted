# Tasks: Politiquera Gazette

## Core Implementation

- [done] **1** Create `public/newspaper.js` — gazette panel UI
- [done] **2** Add gazette styles to `public/styles.css`
- [done] **3** Create `deploy/cache_misdbond2026_gazette.py`
- [done] **4** Create `deploy/cache_elsa2026_gazette.py`
- [done] **5** Create `deploy/generate_statewide_gazette_cache.py`
- [done] **6** Integrate gazette button into `misdbond2026/map.js`
- [done] **7** Integrate gazette button into `elsa2026/map.js`

## Paywall Integration

- [in-progress] **8** Add paywall blur to gazette panel for non-subscribers
- [in-progress] **9** Show "Subscribe to view" overlay on gazette for non-subscribers
- [pending] **10** Test: non-subscriber sees blurred gazette with subscribe CTA
- [pending] **11** Test: subscriber sees full gazette content

## Story Quality

- [pending] **12** Audit all story templates for accuracy — verify numbers match DB
- [pending] **13** Add "Voting Method" story (early vs. election day vs. mail-in split)
- [pending] **14** Add "New Voters" story (first-time voters as % of total)
- [pending] **15** Add "Geographic Story" (highest/lowest turnout neighborhoods)

## New Elections

- [pending] **16** Create gazette cache builder template for future elections (`deploy/cache_TEMPLATE_gazette.py`)
- [pending] **17** Document gazette cache format in `ELECTION_SITE_TEMPLATE_PLAYBOOK.md`

## Status

**Overall**: [in-progress] — gazette is live on both mini-sites, paywall integration incomplete, story quality needs audit.
