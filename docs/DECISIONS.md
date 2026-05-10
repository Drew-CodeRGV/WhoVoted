# Architectural Decision Log — WhoVoted

## ADR-001: SQLite over PostgreSQL

**Date**: 2026-02 (project inception)
**Context**: Needed a database for voter records (150k+ rows), vote history, and district data. Deployment target is a single AWS Lightsail instance.
**Decision**: Use SQLite3 in WAL mode.
**Alternatives**: PostgreSQL, MySQL.
**Consequences**:
- Pro: Zero operational overhead, no separate DB process, trivial backups (copy file), fast reads.
- Pro: WAL mode handles concurrent reads from gunicorn workers.
- Con: Single-writer limitation — not a problem at current scale (writes are batch imports, not concurrent user writes).
- Con: No built-in replication. Backup is manual `cp` or cron.
- Tradeoff: If the platform grows to multi-server, will need to migrate to Postgres. Current single-box architecture makes this acceptable.

---

## ADR-002: Point-in-Polygon District Counting

**Date**: 2026-03
**Context**: Initial district vote counting used coordinate comparisons (e.g., "if lng > -98.12, it's in TX-15"). This produced wildly inaccurate counts because district boundaries are irregular polygons.
**Decision**: Use point-in-polygon algorithm on precinct centroids to map precincts to districts.
**Alternatives**:
- Individual voter coordinate testing (too slow, 150k+ voters × N districts)
- Coordinate bounding boxes (inaccurate for irregular boundaries)
- External geocoding API with district lookup (expensive, rate-limited)
**Consequences**:
- Pro: Accurate counts that match certified election results.
- Pro: Fast — only ~200 precincts to test, not 150k voters.
- Con: Requires GeoJSON boundary files for each district type.
- Con: VTD vintage issue — precincts split after redistricting may map incorrectly.
- This decision is now codified as a mandatory rule in `.kiro/steering/district-counting.md`.

---

## ADR-003: Ollama Local LLM over Hosted API

**Date**: 2026-03
**Context**: Wanted natural language query interface for voter data. Options: OpenAI API, Anthropic API, or local LLM.
**Decision**: Run Ollama with llama3.2:latest on the production server (127.0.0.1:11434).
**Alternatives**:
- OpenAI GPT-4 API (better quality, but $0.03/query adds up, requires API key management, data leaves the server)
- Anthropic Claude API (same cost/privacy concerns)
- No AI search (simpler, but less useful)
**Consequences**:
- Pro: Zero per-query cost. Data never leaves the server. No API key to manage.
- Pro: Acceptable quality for SQL generation with explicit schema prompting.
- Con: Requires ~4GB RAM for the model. Server has 4GB total — tight.
- Con: First query after restart is slow (10–15s model loading).
- Con: Occasionally generates invalid SQL (wrong column names).
- Tradeoff: Quality is "good enough" for the use case. If quality becomes a blocker, can switch to hosted API for premium tier users.

---

## ADR-004: Single-Box AWS Lightsail Deployment

**Date**: 2026-02
**Context**: Need to host the platform. Options range from serverless to dedicated servers.
**Decision**: Single AWS Lightsail instance ($20/mo, 4GB RAM, 2 vCPU).
**Alternatives**:
- AWS ECS/Fargate (container-based, more complex, more expensive)
- Kubernetes (massive overkill for current scale)
- Heroku (simpler but more expensive, less control)
- Vercel/Netlify (frontend only, can't run Flask backend)
**Consequences**:
- Pro: Simple. One box, one deploy target, one set of logs.
- Pro: Cheap ($20/mo covers everything).
- Pro: Full control over the environment.
- Con: Single point of failure. No auto-scaling.
- Con: 4GB RAM is tight with Ollama loaded.
- Tradeoff: Acceptable for current user base (<100 concurrent). If traffic spikes, can vertically scale the Lightsail instance or add a CDN for static assets.

---

## ADR-005: Gunicorn + Supervisor + Nginx

**Date**: 2026-02
**Context**: Need a production WSGI server, process manager, and reverse proxy.
**Decision**: gunicorn (WSGI), supervisor (process manager), nginx (reverse proxy + static files + TLS).
**Alternatives**:
- systemd instead of supervisor (less visibility, harder to manage multiple apps)
- uWSGI instead of gunicorn (more complex config, marginal performance gain)
- Caddy instead of nginx (simpler TLS, but less ecosystem support)
- Docker Compose (adds container overhead on a 4GB box)
**Consequences**:
- Pro: Battle-tested stack. Extensive documentation.
- Pro: Supervisor makes it easy to manage multiple apps (whovoted + d15).
- Pro: nginx handles static files efficiently, TLS termination, and rate limiting.
- Con: Three config files to maintain (gunicorn_config.py, supervisor conf, nginx conf).
- This is the standard Python web deployment stack. No regrets.

---

## ADR-006: Nominatim Primary + AWS Location Fallback for Geocoding

**Date**: 2026-02
**Context**: Need to geocode voter addresses (street address → lat/lng). 150k+ addresses.
**Decision**: Nominatim (OpenStreetMap) as primary geocoder, AWS Location Service as fallback.
**Alternatives**:
- Google Geocoding API (expensive at scale, $5/1000 requests)
- AWS Location only (good quality but costs money per request)
- Nominatim only (free but rate-limited to 1 req/s, sometimes inaccurate for rural TX)
**Consequences**:
- Pro: Nominatim is free and handles most addresses correctly.
- Pro: AWS Location catches the ~5% that Nominatim misses (rural addresses, new subdivisions).
- Pro: Geocoding cache means each address is only looked up once.
- Con: Nominatim rate limit (1 req/s) means initial geocoding of 150k addresses takes days.
- Con: AWS Location costs ~$0.50/1000 requests (acceptable for fallback volume).

---

## ADR-007: Separate d15_app.py Process

**Date**: 2026-03
**Context**: The TX-15 congressional district dashboard has different data needs and access patterns than the main app. It was initially part of app.py but grew complex.
**Decision**: Run `backend/d15_app.py` as a separate Flask process on port 5001, proxied by nginx.
**Alternatives**:
- Keep in main app.py (growing monolith, harder to restart independently)
- Separate repo (overkill, shares the same DB and data)
**Consequences**:
- Pro: Can restart d15 without affecting main app.
- Pro: Cleaner code separation.
- Con: Two supervisor processes to manage.
- Con: Shares the same SQLite DB (WAL handles concurrent reads fine).

---

## ADR-008: backend/app.py Replaced Root app.py Monolith

**Date**: 2026-02
**Context**: The original `app.py` in the repo root was a monolithic Flask app with everything in one file. As features grew, it became unmaintainable.
**Decision**: Move to `backend/app.py` with modular imports (auth.py, upload.py, processor.py, etc.).
**Alternatives**:
- Keep monolith (unmaintainable past ~1000 lines)
- Full Django migration (too much work for the benefit)
- FastAPI (would require rewriting all routes)
**Consequences**:
- Pro: Clean module separation. Each file has a single responsibility.
- Pro: Easier to test individual modules.
- Con: The old `app.py` still exists in the repo root (confusing for new developers).
- Action: The old root `app.py` should be deleted or clearly marked as deprecated.

---

## ADR-009: EVR Scraper Architecture (Texas-Specific, Extensible Design)

**Date**: 2026-03
**Context**: Need automated early-voting data collection. Texas SOS provides data via the Civix platform API.
**Decision**: Single Python script (`deploy/evr_scraper.py`) with a config dict for election filters. Designed to be extensible to other states but currently Texas-only.
**Alternatives**:
- Scrapy framework (overkill for a single API)
- Separate microservice (overkill for a cron job)
- Manual upload only (defeats the purpose of real-time data)
**Consequences**:
- Pro: Simple. One file, one cron entry.
- Pro: `ELECTION_FILTERS` dict makes it easy to add new elections.
- Con: Civix API is undocumented and has changed endpoints before.
- Con: If the API changes, the scraper breaks silently (need alerting).
- Future: To add another state, create a new scraper class with the same interface.

---

## ADR-010: Kiro Steering Files for AI Assistant Constraints

**Date**: 2026-02
**Context**: AI assistants (Kiro, Claude Code) working on this codebase kept making the same mistakes: using PostgreSQL syntax, wrong column names, coordinate comparisons for districts.
**Decision**: Create `.kiro/steering/*.md` files with always-loaded rules that constrain AI behavior.
**Alternatives**:
- README-only documentation (AI doesn't always read it)
- Code comments (scattered, easy to miss)
- No constraints (leads to repeated mistakes)
**Consequences**:
- Pro: AI assistants consistently use correct patterns (SQLite syntax, point-in-polygon, git-based deploy).
- Pro: Rules are version-controlled and evolve with the project.
- Pro: New AI sessions start with correct context immediately.
- Con: Adds ~3 files to maintain. Must be updated when patterns change.
- This approach has been highly effective at preventing recurring AI mistakes.

---

## ADR-011: Per-Election Credit Model over Monthly Subscription (Initial Launch)

**Date**: 2026-04
**Context**: Needed a revenue model. Options: monthly SaaS subscription or per-election credits.
**Decision**: Launch with per-election credits ($10/election) first. 4-tier SaaS subscription planned for later.
**Alternatives**:
- Monthly subscription only (higher barrier to entry for casual users)
- Free with ads (doesn't work for niche political data)
- Per-query pricing (too complex, unpredictable for users)
**Consequences**:
- Pro: Low barrier to entry ($10 for one election).
- Pro: Simple to implement (single Stripe Payment Link, webhook creates credit).
- Pro: Users pay only for what they use.
- Con: Low revenue per user compared to monthly subscription.
- Con: No recurring revenue (must re-sell each election cycle).
- Plan: Layer the 4-tier SaaS model on top for power users who want ongoing access.

---

## ADR-012: Static JSON Cache Files over Real-Time DB Queries

**Date**: 2026-03
**Context**: Election mini-sites need to serve voter data, report cards, and gazette content. Options: query DB on every request, or pre-build JSON cache files.
**Decision**: Pre-build static JSON cache files. Serve via nginx. Rebuild on data changes.
**Alternatives**:
- Real-time DB queries (slow for 150k+ voter datasets, especially with JOINs)
- Redis cache (adds operational complexity)
- CDN (overkill for current traffic)
**Consequences**:
- Pro: Instant response times (nginx serves static files).
- Pro: No DB load from public traffic.
- Pro: Cache files can be inspected/debugged directly.
- Con: Cache can become stale if rebuild isn't triggered after data changes.
- Con: Disk usage grows with each election (acceptable — JSON compresses well).
- Mitigation: `cache_invalidate()` function triggers rebuild after imports.
