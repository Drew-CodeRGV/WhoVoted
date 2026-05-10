# Design: EVR Scraper Rewrite

## Current Architecture

`deploy/evr_scraper.py` uses two Civix API endpoints:

1. `GET /api-ivis-system/api/v1/getFile?type=EVR_ELECTION`
   - Returns base64-encoded JSON with elections list, dates, county IDs
2. `GET /api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE&electionId={id}&electionDate={date}`
   - Downloads statewide CSV for a given election + date

The script filters elections via `ELECTION_FILTERS` dict (election name substring → DB metadata), imports rows into `voter_elections`, and writes a state file.

## Known Issues to Fix

1. **Cron path**: Verify `/opt/whovoted/venv/bin/python3` exists and has `requests`/`database` importable.
2. **ELECTION_FILTERS**: Must be updated for current election cycle (2026 primary, May 2026 special elections).
3. **Duplicate prevention**: Confirm `INSERT OR IGNORE` or `ON CONFLICT DO NOTHING` is used.
4. **Cache invalidation**: After import, call `cache_invalidate()` via HTTP to the local Flask app, or directly clear the cache file.
5. **API endpoint stability**: Civix has changed endpoints before. Add a health-check step at the top.

## Proposed Structure

```python
# deploy/evr_scraper.py

ELECTION_FILTERS = {
    '2026 REPUBLICAN PRIMARY': ('2026-03-03', '2026', 'primary', 'Republican'),
    '2026 DEMOCRATIC PRIMARY': ('2026-03-03', '2026', 'primary', 'Democratic'),
    '2026 MAY UNIFORM ELECTION': ('2026-05-02', '2026', 'general', None),
    # Add new elections here
}

def fetch_elections_list() -> list: ...
def fetch_statewide_csv(election_id, election_date) -> list[dict]: ...
def import_rows(rows, election_meta) -> int: ...  # returns count inserted
def invalidate_cache(): ...  # POST to /api/admin/cache-invalidate or delete cache files
def main(): ...
```

## Duplicate Prevention

```sql
INSERT OR IGNORE INTO voter_elections (vuid, election_date, election_year, election_type, voting_method, party_voted)
VALUES (?, ?, ?, ?, ?, ?)
```

The `(vuid, election_date, voting_method)` combination should be UNIQUE. Verify this constraint exists.

## Cache Invalidation After Import

Option A (preferred): HTTP call to local Flask app
```python
import urllib.request
urllib.request.urlopen('http://127.0.0.1:5000/api/admin/cache-invalidate', timeout=5)
```

Option B: Delete cache files directly
```python
import glob
for f in glob.glob('/opt/whovoted/public/cache/*.json'):
    os.remove(f)
```

## State File Format

```json
{
  "last_run": "2026-03-03T18:00:00",
  "last_success": "2026-03-03T18:00:00",
  "elections_processed": ["2026 REPUBLICAN PRIMARY"],
  "rows_imported": 1247,
  "errors": []
}
```

## Extensibility for Other States

- `CIVIX_BASE` is already a config constant
- `ELECTION_FILTERS` is already a config dict
- To add another state: add a new scraper class with the same `fetch_elections_list()` / `fetch_statewide_csv()` interface
- Main script dispatches to state-specific scrapers

## Files Touched

- `deploy/evr_scraper.py` — primary fix target
- `backend/database.py` — verify UNIQUE constraint on `voter_elections`
- `backend/app.py` — add `/api/admin/cache-invalidate` endpoint if not present

## Alternatives Considered

- **Replace with manual upload**: Rejected — defeats the purpose of automation.
- **Webhook from Civix**: Not available; polling is the only option.
- **Separate microservice**: Overkill for a cron script.
