# Kiro History — WhoVoted Project Trajectory

A chronological digest of major decisions, explorations, and recurring themes across all WhoVoted Kiro sessions. Written for a successor AI (Claude Code) to understand how the project got to its current state.

---

## Phase 1: Foundation (February 2026)

### Initial Build
The project started as a Google Maps-based voter mapping tool. The first Kiro session modernized it completely:
- Migrated from Google Maps to OpenStreetMap/Leaflet (eliminating API key dependency)
- Built Flask backend with admin panel, CSV upload, geocoding pipeline
- Established the `backend/` module structure (app.py, auth.py, upload.py, processor.py, geocoder.py)
- Set up Nominatim geocoding with persistent JSON cache

### Deployment
- Deployed to AWS Lightsail ($20/mo instance)
- Set up gunicorn + supervisor + nginx stack
- Configured Let's Encrypt TLS for politiquera.com
- Established git-based deployment workflow

### Key Decision: SQLite
Chose SQLite over PostgreSQL for simplicity. The voter data (150k+ rows) fits comfortably. WAL mode handles concurrent reads from gunicorn workers. This decision has held up well.

---

## Phase 2: Voter Data Pipeline (Late February – Early March 2026)

### Texas SOS Data Integration
- Built CSV import pipeline for Texas voter registration files
- Implemented batch geocoding (Nominatim primary, AWS Location fallback)
- Created the `voter_elections` table for vote history tracking
- Imported Hidalgo County voter rolls and election history

### EVR Scraper
- Built `deploy/evr_scraper.py` to fetch early-voting data from Texas SOS Civix API
- Set up cron job (every 6 hours during election season)
- The Civix API is undocumented and fragile — has broken multiple times

### Recurring Theme: Data Accuracy
From this point forward, a huge amount of session time was spent on data accuracy:
- Reconciling county-level uploads with statewide data
- Fixing duplicate vote records
- Handling voters who appear in multiple counties
- Debugging geocoding failures for rural addresses

---

## Phase 3: District System Crisis (March 2026)

### The Accuracy Crisis
The initial district counting approach used coordinate comparisons (e.g., "if lng > -98.12, it's in TX-15"). This produced wildly wrong counts. Multiple sessions were spent debugging why district totals didn't match certified results.

### The Fix: Point-in-Polygon
After much investigation, the solution was clear: use point-in-polygon on precinct centroids. This became the mandatory methodology, codified in `.kiro/steering/district-counting.md`.

The fix required:
1. Obtaining GeoJSON boundary files for all district types
2. Calculating precinct centroids from voter coordinates
3. Testing centroids against district polygons
4. Rebuilding all district assignments

### Commissioner Precinct 2 (CPCT2) Saga
CPCT2 was particularly problematic. The automated mapping produced wrong counts because some precincts were split between commissioner precincts. The fix required manually specifying the correct precinct list based on certified election results. This consumed multiple sessions.

### VTD Vintage Issue
Discovered that VTD (Voting Tabulation District) boundary files are from the 2020 redistricting cycle. Precincts renumbered after 2022 may map incorrectly. This is a known limitation, not fully resolved.

### State House and Senate Districts
Extended the district system to cover state house (HD-*) and state senate (SD-*) districts. Same point-in-polygon methodology. Required obtaining additional boundary files from the Texas Legislative Council.

---

## Phase 4: Election Mini-Sites (March – April 2026)

### TX-15 Dashboard (d15_app.py)
Built a dedicated dashboard for TX-15 congressional district analysis. Ran as a separate Flask process on port 5001. This was the first "election-specific" view.

### McAllen ISD Bond 2026 (misdbond2026)
Built the first full election mini-site at `/misdbond2026/`:
- Voter map with dots for all bond election voters
- Report cards (campus-level, district-level)
- Staff and student overlays
- Gazette (data-driven stories)
- Cache builders for all data layers

### Elsa 2026 (elsa2026)
Second election mini-site, following the same pattern as misdbond2026. Established the template for future election sites.

### Election Site Template
After building two mini-sites, documented the pattern in `ELECTION_SITE_TEMPLATE_PLAYBOOK.md`. Each new election follows the same structure: `public/{slug}/`, cache builders in `deploy/`, optional dedicated API Blueprint.

---

## Phase 5: AI Search (March 2026)

### Ollama Integration
Added natural language query interface using Ollama (llama3.2:latest) running locally:
- `backend/llm_query.py` — converts questions to SQL
- `backend/llm_api_endpoint.py` — Flask endpoint
- `public/llm-chat.js` — chat panel UI

### Timeout Issues
The LLM was initially unreliable — Ollama would hang or take 60+ seconds. Added 30-second timeout via threading. Multiple sessions were spent debugging timeout issues.

### Schema Context
The LLM needs the DB schema in its prompt to generate correct SQL. This schema string must be manually maintained. When columns were added (e.g., `state_senate_district`), the LLM would generate wrong SQL until the schema context was updated.

---

## Phase 6: Gazette / Newspaper Feature (April 2026)

### Data-Driven Stories
Built the "Politiquera Gazette" — a newspaper-style panel that generates stories from voter data:
- Turnout summaries
- Party breakdowns
- Demographic analysis
- Precinct performance rankings

### Implementation
Stories are pre-generated by Python scripts (template + data substitution, no LLM) and cached as JSON. The frontend (`newspaper.js`) renders them as styled article cards.

---

## Phase 7: Subscription System (April – May 2026)

### Per-Election Credits (Implemented)
Built the per-election credit system:
- $10 per election credit via Stripe Payment Link
- Credits are purchased, then explicitly redeemed against a specific election
- Webhook-driven credit creation
- Admin portal for managing users, credits, subscriptions

### 4-Tier SaaS (Designed, Not Implemented)
Designed a full SaaS subscription model ($50–$450/mo) with campaign workspaces, list building, turf cutting, etc. This is documented in `SUBSCRIPTION_IMPLEMENTATION_PLAN.md` and `SUBSCRIPTION_TIERS_ANALYSIS.md` but has not been built.

### Paywall
Built `public/paywall.js` to gate election content:
- Non-subscribers see voter dots but not popup details
- Report card, gazette, search are blurred with "Subscribe" overlay
- Integration into mini-sites is partially complete

---

## Phase 8: Deploy Cleanup (May 2026)

### The Problem
Over ~50 Kiro sessions, the `deploy/` directory accumulated 300+ scripts. Most are one-off diagnostics (`check_*.py`, `verify_*.py`, `fix_*.py`) that were run once and never needed again.

### The Solution (In Progress)
Mass deletion of one-off scripts, keeping only:
- Cron scripts (evr_scraper, import_may2_roster)
- Reusable utilities (geocoding, cache builders)
- Active election support scripts

---

## Recurring Themes

### 1. Data Accuracy is the Hardest Problem
More session time was spent on data accuracy than any other concern. District counts, geocoding accuracy, duplicate records, precinct mapping — these are the core challenges.

### 2. The Deploy Directory Grows Unbounded
Every debugging session produces 5–10 new scripts. Without discipline, `deploy/` becomes a junk drawer. Need a naming convention and regular cleanup.

### 3. Stale Documentation Accumulates
Each Kiro session produces `*_COMPLETE.md`, `*_STATUS.md`, `*_SUMMARY.md` files. These are session artifacts, not documentation. They should be deleted after the session.

### 4. The Steering Files Work
The `.kiro/steering/` approach has been highly effective at preventing recurring AI mistakes. The district-counting rule alone has saved dozens of hours of debugging.

### 5. Single-Box Simplicity Pays Off
The single Lightsail instance with SQLite has been remarkably reliable. No container orchestration, no managed databases, no multi-service coordination. The simplicity is a feature.

### 6. Election Sites Follow a Pattern
After building two mini-sites (misdbond2026, elsa2026), the pattern is clear and repeatable. Each new election is a copy of the template with election-specific data.

---

## Ideas Explored and Dropped

- **PostgreSQL migration**: Considered multiple times, always rejected. SQLite handles the load.
- **Docker deployment**: Considered, rejected — adds complexity on a 4GB box with no benefit.
- **Real-time websocket updates**: Considered for election day. Rejected — polling every 30s is sufficient.
- **OpenAI/Anthropic API for AI search**: Considered, rejected — cost and privacy concerns. Local Ollama is "good enough."
- **Multi-state expansion**: Designed for but not built. The EVR scraper is extensible; the rest is Texas-specific.
- **Mobile app (PWA)**: Mentioned in early sessions, never pursued. The responsive web UI is sufficient.
- **Redis for caching**: Considered, rejected — SQLite WAL + static JSON files handle the load.

---

## Current State (May 2026)

- **Working**: Voter map, district analytics, election mini-sites, gazette, AI search, admin dashboard, per-election paywall (partial)
- **Broken**: EVR scraper (needs verification), paywall integration (incomplete)
- **Planned**: 4-tier SaaS subscription, deploy cleanup, multi-county expansion
- **Technical debt**: 300+ deploy scripts, 140+ stale markdown files, sessions.json → SQLite migration
