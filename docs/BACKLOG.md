# WhoVoted Backlog

## Data Quality

| Item | Priority | Blocker | Effort |
|------|----------|---------|--------|
| Fix unmapped precincts (NULL district assignments) | P1 | Need statewide voter file precinct→VTD mapping | 1 day |
| Verify state senate district assignments against certified results | P1 | None | 2 hours |
| Investigate VTD vintage issue (precincts split after 2022) | P2 | Need updated VTD boundary files from TLC | 1 day |
| Backfill geocoding for voters with NULL lat/lng | P2 | Nominatim rate limit (1 req/s) | 3 days |
| Audit CPCT2 precinct list against 2026 certified results | P1 | Election must be certified first | 2 hours |
| Multi-county district assignment (Brooks, Cameron, Willacy) | P2 | Need boundary files for those counties | 2 days |
| Reconcile statewide EVR data with county-level uploads | P2 | None | 1 day |
| Add `state_senate_district` to LLM schema context | P1 | None | 15 min |

## Subscriptions

| Item | Priority | Blocker | Effort |
|------|----------|---------|--------|
| Complete paywall integration for misdbond2026 | P0 | None | 1 day |
| Complete paywall integration for elsa2026 | P0 | None | 1 day |
| Generate teaser cache files (heatmap only, no PII) | P1 | None | 4 hours |
| Implement 4-tier SaaS subscription system | P2 | Stripe Products/Prices need to be created | 4 weeks |
| Add subscription expiration banner (30 days before expiry) | P2 | Per-election paywall must be complete | 2 hours |
| Email verification via AWS SES | P1 | SES production access (currently sandbox) | 1 day |
| SMS verification via AWS SNS | P1 | SNS sandbox exit (need phone number) | 1 day |
| Migrate sessions from sessions.json to SQLite | P1 | None | 4 hours |

## EVR Scraper

| Item | Priority | Blocker | Effort |
|------|----------|---------|--------|
| Verify Civix API endpoints still respond | P0 | SSH to server | 30 min |
| Update ELECTION_FILTERS for current election cycle | P0 | None | 30 min |
| Add cache invalidation after successful import | P1 | None | 1 hour |
| Add alerting on 3 consecutive failures | P2 | SES production access | 2 hours |
| Make scraper extensible to other states | P2 | None | 1 day |

## UI/UX

| Item | Priority | Blocker | Effort |
|------|----------|---------|--------|
| Mobile-responsive gazette panel | P1 | None | 4 hours |
| Streaming LLM response (SSE) to avoid 30s silent wait | P2 | None | 1 day |
| Query history in AI search (localStorage) | P2 | None | 2 hours |
| Paywall modal design polish | P1 | None | 2 hours |
| Subscribe page UX: single-page flow with progress indicator | P1 | None | 1 day |
| Account page: show credits, subscriptions, billing | P1 | None | 1 day |
| Admin dashboard: subscription management tab | P1 | None | 1 day |

## Infrastructure

| Item | Priority | Blocker | Effort |
|------|----------|---------|--------|
| Deploy directory cleanup (~200 one-off scripts) | P1 | Need to audit which scripts are still needed | 2 hours |
| Set up log rotation for gunicorn-error.log | P1 | None | 30 min |
| Set up log rotation for evr_scraper.log | P1 | None | 30 min |
| Monitor disk usage on /opt/whovoted/data/ | P2 | None | 1 hour |
| Add health check endpoint (`GET /health`) | P1 | None | 15 min |
| Certbot auto-renewal verification | P1 | None | 15 min |
| Backup strategy for SQLite DB | P1 | None | 2 hours |
| WAL checkpoint cron job | P2 | None | 30 min |
| Upgrade Ollama to latest version | P2 | None | 30 min |

## Special Elections

| Item | Priority | Blocker | Effort |
|------|----------|---------|--------|
| MISD 2015 Bond historical comparison overlay | P2 | Data imported | 1 day |
| Template playbook for new election sites | P1 | None | 2 hours |
| Automated cache rebuild on data import | P2 | None | 4 hours |

## Should Probably Delete

| Item | Reason |
|------|--------|
| ~140 `*_COMPLETE.md` / `*_STATUS.md` files in repo root | Stale Kiro session dumps, not documentation |
| `UPLOAD_*.ps1` scripts in repo root | One-off upload scripts, never needed again |
| `POWERSHELL_RULES.md` | Kiro-specific, not project documentation |
| `OPTIMIZATION_GUIDE.md`, `OPTIMIZATION_STRATEGY.md` | Stale session dumps |
| `QUICK_UPLOAD_COMMANDS.md`, `SIMPLE_UPLOAD_INSTRUCTIONS.md` | One-off instructions |
