# Spec: EVR Scraper Rewrite

## Problem

The Texas early-voting turnout scraper (`deploy/evr_scraper.py`) fetches data from the Texas SOS Civix platform every 6 hours during election season. The cron job is currently broken — the script may have been deleted or moved during a deploy cleanup, or the Civix API endpoints may have changed. During active elections, this scraper is the primary data source for real-time turnout numbers.

## Users

- Platform operator: needs automated turnout data without manual uploads
- End users: see live early-voting counts update throughout election day

## Acceptance Criteria

1. Script runs successfully from cron: `0 6,12,18,23 * * * /opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/evr_scraper.py`
2. Fetches statewide EVR data from Texas SOS Civix API (`goelect.txelections.civixapps.com`)
3. Imports new voter records into `voter_elections` table without duplicates
4. Writes a state file (`/opt/whovoted/data/evr_scraper_state.json`) to track last successful run
5. Logs to `/opt/whovoted/data/evr_scraper.log`
6. On failure, logs the error and exits cleanly (does not crash cron)
7. Idempotent: re-running with the same data does not create duplicates
8. Supports multiple elections via `ELECTION_FILTERS` config dict
9. After successful import, invalidates the in-memory query cache (calls `cache_invalidate()` or equivalent)
10. Script is extensible to other states (not Texas-only hardcoded)

## Current State

- `deploy/evr_scraper.py` exists in the repo (confirmed present as of this spec)
- Cron entry exists in ubuntu user crontab
- **Broken**: needs verification that the Civix API endpoints still respond and the script runs end-to-end
- The `ELECTION_FILTERS` dict needs to be updated for the current election cycle

## Out of Scope

- Real-time websocket push to frontend (polling is sufficient)
- Multi-state support beyond Texas (design for it, don't build it yet)
