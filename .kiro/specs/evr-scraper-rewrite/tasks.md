# Tasks: EVR Scraper Rewrite

- [in-progress] **1** Verify `deploy/evr_scraper.py` exists on production server at `/opt/whovoted/deploy/evr_scraper.py`
- [pending] **2** Test Civix API endpoints manually: `curl "https://goelect.txelections.civixapps.com/api-ivis-system/api/v1/getFile?type=EVR_ELECTION"`
- [pending] **3** Update `ELECTION_FILTERS` for current election cycle (2026 primary + May 2026 specials)
- [pending] **4** Verify `voter_elections` has UNIQUE constraint on `(vuid, election_date, voting_method)`; add if missing
- [pending] **5** Add `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING` to all insert statements
- [pending] **6** Add cache invalidation step after successful import
- [pending] **7** Add `/api/admin/cache-invalidate` endpoint to `app.py` (superadmin only) if not present
- [pending] **8** Test end-to-end: run script manually, verify rows appear in DB, verify cache clears
- [pending] **9** Verify cron entry is correct: `0 6,12,18,23 * * * /opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/evr_scraper.py`
- [pending] **10** Monitor first automated run; check `/opt/whovoted/data/evr_scraper.log`
- [pending] **11** Add alerting: if scraper fails 3 consecutive runs, send email via SES to drew@politiquera.com

## Status

**Overall**: [in-progress] — script exists, cron entry exists, but end-to-end functionality unverified. Blocked on confirming Civix API is still responding and ELECTION_FILTERS is current.
