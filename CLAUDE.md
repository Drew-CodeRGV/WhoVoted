# CLAUDE.md — WhoVoted Reference Card

## What WhoVoted Is

WhoVoted is a Texas voter-data platform for political campaigns, consultants, and researchers. It maps geocoded voter rolls, tracks early-voting turnout in real time, and provides district-level analytics. Production deployment is at **politiquera.com**. Primary users are South Texas political operatives and campaigns. The platform is subscription-gated (per-election credits, $10/election) with a free teaser view.

---

## Production Architecture

```
nginx (politiquera.com, Let's Encrypt)
  └─► gunicorn → backend/app.py  (port 5000, supervisor: "whovoted")
  └─► gunicorn → backend/d15_app.py  (port 5001, supervisor: "d15")
```

- **Entry point**: `/opt/whovoted/backend/app.py` — this is the production app.
- **NOT the production app**: `app.py` in the repo root is an old monolith. Ignore it.
- **Supervisor config**: `/etc/supervisor/conf.d/whovoted.conf`
- **Gunicorn config**: `/opt/whovoted/gunicorn_config.py`
- **nginx config**: `/etc/nginx/sites-enabled/politiquera.com`
- **d15_app.py**: Secondary Flask app on port 5001 for TX-15 congressional district dashboard.
- **Static files**: served by nginx from `/opt/whovoted/public/`
- **Cache files**: `/opt/whovoted/public/cache/` — pre-built JSON, served directly by nginx

---

## Deployment Workflow

See `.kiro/steering/server-access.md` for full detail.

**Standard deploy (from local):**
```bash
git commit -am "message"
git push origin main
ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com
cd /opt/whovoted && git pull origin main
sudo supervisorctl restart whovoted
```

**When Claude Code is running ON the production server:**
- Edits to `/opt/whovoted/backend/` are live after `sudo supervisorctl restart whovoted`.
- Still required: `git commit && git push` to keep the repo in sync.
- Never skip the git sync — the repo is the source of truth.

**Restart commands:**
```bash
sudo supervisorctl restart whovoted      # main app
sudo supervisorctl restart d15           # d15 dashboard
sudo supervisorctl status                # check both
sudo nginx -t && sudo systemctl reload nginx
```

---

## Database

**Type**: SQLite3 (WAL mode)
**Path**: `/opt/whovoted/data/whovoted.db`
**Connection**: `sqlite3.connect('/opt/whovoted/data/whovoted.db')`
**Placeholders**: `?` — NEVER `%s`

### Key Tables

**voters**
- `vuid` TEXT PRIMARY KEY
- `precinct` TEXT — NOT `voting_precinct`
- `lat` REAL — NOT `latitude`
- `lng` REAL — NOT `longitude`
- `county` TEXT
- `congressional_district` TEXT
- `state_house_district` TEXT
- `state_senate_district` TEXT
- `commissioner_district` TEXT
- `firstname`, `lastname`, `birth_year`, `sex`, `address`, `city`, `zip`
- `current_party` TEXT — most recent primary voted
- `geocoded` INTEGER — 1 if geocoded

**voter_elections**
- `vuid` TEXT
- `election_date` TEXT (YYYY-MM-DD)
- `election_year` TEXT
- `election_type` TEXT — 'primary', 'general', 'runoff'
- `voting_method` TEXT — 'early-voting', 'election-day', 'mail-in'
- `party_voted` TEXT — 'Democratic', 'Republican'
- `is_new_voter` INTEGER

**district_counts_cache**
- `district_type`, `district_number`, `county`
- `total_voters`, `voted_2024_general`, `voted_2024_primary`

**Subscription tables** (added 2026):
- `users` — extended with `password_hash`, `phone`, `auth_method`, `verified`, `stripe_customer_id`
- `credits` — `id`, `user_id`, `stripe_payment_id`, `purchased_at`, `redeemed_at`, `redeemed_election_slug`
- `subscriptions` — `id`, `user_id`, `election_slug`, `status`, `current_period_end`, `credit_id`, `payment_type`
- `verification_codes` — `id`, `user_id`, `code`, `channel`, `expires_at`, `used`
- `sessions` — `token`, `user_id`, `role`, `email`, `expires_at`
- `elections` — `slug`, `name`, `description`, `election_date`, `price_cents`, `active`

**Always check schema before writing queries:**
```python
conn.execute('PRAGMA table_info(table_name)').fetchall()
conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
```

**Never assume**: PostgreSQL syntax, `%s` placeholders, column names `voting_precinct` / `latitude` / `longitude`, table names `early_voting` / `election_day`.

---

## District Counting — Mandatory Methodology

For ALL districts in ALL counties: **point-in-polygon precinct→district mapping only.**

1. Load district polygon boundaries from GeoJSON (`/opt/whovoted/public/data/districts.json`)
2. Calculate precinct centroid: `AVG(lat)`, `AVG(lng)` of voters in that precinct
3. Test centroid against district polygon using `point_in_polygon(lng, lat, geometry)`
4. Build `precinct → district_id` mapping
5. Count votes from `voter_elections` WHERE `vuid` IN voters with those precincts

**Never use**: approximate lat/lng boundaries, coordinate comparisons (`lng > -98.12`), individual voter coordinates for district assignment.

```python
# Canonical pattern
cur.execute("""
    SELECT precinct, AVG(lat), AVG(lng), COUNT(*)
    FROM voters WHERE county = ? AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""", (county,))
for precinct, lat, lng, count in cur.fetchall():
    for district in districts:
        if point_in_polygon(lng, lat, district['geometry']):
            precinct_to_district[precinct] = district['properties']['district_id']

precincts = [p for p, d in precinct_to_district.items() if d == target_district]
placeholders = ','.join('?' * len(precincts))
cur.execute(f"""
    SELECT COUNT(DISTINCT v.vuid)
    FROM voters v INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders}) AND ve.election_date = ?
""", [county] + precincts + [election_date])
```

**Known accuracy gap**: VTD boundary files are from the 2020 redistricting cycle. Precincts that were split or renumbered after 2022 may map incorrectly. This is a known limitation, not a bug.

---

## External Services

| Service | Address | Purpose |
|---------|---------|---------|
| Ollama | `127.0.0.1:11434` | Local LLM for AI search |
| Current model | `llama3.2:latest` | Natural language → SQL |
| Nominatim | `nominatim.openstreetmap.org` | Primary geocoder (rate-limited 1 req/s) |
| AWS Location Service | boto3, `us-east-1` | Optional geocoding fallback |
| AWS SES | boto3 | Email verification codes |
| AWS SNS | boto3 | SMS verification codes |
| Stripe | Payment Link `https://buy.stripe.com/7sY6oG74E41e8FM7tx4gg00` | $10/credit purchases |

---

## Cron Jobs (ubuntu user)

```
0 6,12,18,23 * * *  /opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/evr_scraper.py
*/10 * * * *         /opt/whovoted/venv/bin/python3 /opt/whovoted/deploy/import_may2_roster.py
```

**EVR scraper**: Fetches Texas SOS Civix API for early-voting turnout data. **Currently broken** — the cron path may be stale; verify the script exists and the Civix API endpoints are still responding. See spec `evr-scraper-rewrite`.

**May 2 roster importer**: Imports official voter roster for the May 2, 2026 election. Active during election season; should be disabled or made idempotent after election day.

---

## Doc Landscape Rule

The ~140 `*_COMPLETE.md`, `*_STATUS.md`, `*_SUMMARY.md`, `*_IMPLEMENTATION.md`, `*_READY.md`, `*_FIX.md` files in the repo root are **stale Kiro session dumps**. They document what was done in individual AI sessions. They are NOT current documentation and should not be trusted as authoritative.

**Authoritative docs:**
- `README.md` — user-facing overview
- `ARCHITECTURE.md` — system architecture
- `CHANGELOG.md` — version history
- `.kiro/PROJECT_CONFIG.md` — AI assistant rules (district counting, DB schema, deployment)
- `.kiro/steering/*.md` — always-loaded AI steering rules
- `docs/BACKLOG.md` — current backlog
- `docs/DECISIONS.md` — architectural decision log
- `.kiro/specs/*/` — feature specs

---

## Response Style

- Generate code immediately. No "I'm about to..." preamble.
- Do not confirm user statements ("You're right that...").
- No unnecessary documentation files.
- Check schema before writing queries.
- Terse explanations; verbose code.
- Fix errors without narrating the fix.

---

## Common Commands

```bash
# Restart app
sudo supervisorctl restart whovoted

# Watch logs
tail -f /opt/whovoted/logs/gunicorn-error.log
tail -f /opt/whovoted/data/evr_scraper.log

# Database
sqlite3 /opt/whovoted/data/whovoted.db
sqlite3 /opt/whovoted/data/whovoted.db ".tables"
sqlite3 /opt/whovoted/data/whovoted.db "PRAGMA table_info(voters);"

# Check Ollama
curl http://127.0.0.1:11434/api/tags
ollama list

# Supervisor status
sudo supervisorctl status

# nginx
sudo nginx -t
sudo systemctl reload nginx
sudo tail -f /var/log/nginx/error.log

# Disk
df -h /opt/whovoted
du -sh /opt/whovoted/data/
du -sh /opt/whovoted/logs/
```

---

## Key File Locations (Server)

| Path | Purpose |
|------|---------|
| `/opt/whovoted/backend/app.py` | Production Flask app |
| `/opt/whovoted/backend/d15_app.py` | TX-15 dashboard app |
| `/opt/whovoted/data/whovoted.db` | SQLite database |
| `/opt/whovoted/public/` | Static frontend files |
| `/opt/whovoted/public/cache/` | Pre-built JSON cache |
| `/opt/whovoted/public/data/districts.json` | District GeoJSON boundaries |
| `/opt/whovoted/logs/gunicorn-error.log` | App error log |
| `/opt/whovoted/data/evr_scraper.log` | EVR scraper log |
| `/opt/whovoted/.env` | Environment variables (not in git) |
| `/etc/supervisor/conf.d/whovoted.conf` | Supervisor config |
| `/etc/nginx/sites-enabled/politiquera.com` | nginx config |
| `/opt/whovoted/gunicorn_config.py` | Gunicorn config |
