# Automated Data Update System (Multi-State Extensible)

## Overview
Automated system that pulls voter data from state election systems every 4 hours, detects changes, updates database, and logs everything in admin dashboard. Designed to support multiple states with pluggable state-specific adapters.

## Architecture

### Multi-State Design
```
┌─────────────────────────────────────────┐
│     Auto Update Orchestrator            │
│  (deploy/auto_update_orchestrator.py)   │
└──────────────┬──────────────────────────┘
               │
               ├─► State Adapter: Texas
               │   └─► EVR Scraper
               │   └─► Election Day Scraper
               │
               ├─► State Adapter: [Future State]
               │   └─► State-specific scrapers
               │
               └─► State Adapter: [Future State]
                   └─► State-specific scrapers
```

### State Configuration
```json
{
  "states": {
    "TX": {
      "enabled": true,
      "name": "Texas",
      "adapter": "texas_adapter",
      "update_interval_hours": 4,
      "data_sources": ["EVR", "ELECTION_DAY"],
      "api_config": {
        "base_url": "https://goelect.txelections.civixapps.com",
        "endpoints": {
          "evr": "/api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE",
          "election_day": "/api-ivis-system/api/v1/getFile?type=EVR_STATEWIDE_ELECTIONDAY"
        }
      }
    }
  }
}
```

## Components

### 1. Core Orchestrator (`deploy/auto_update_orchestrator.py`)
- Loads state configurations
- Manages update schedule per state
- Coordinates state adapters
- Handles errors and retries
- Logs all operations

### 2. State Adapter Interface (`deploy/adapters/base_adapter.py`)
```python
class StateAdapter:
    def fetch_data(self, data_source, election_id, election_date)
    def parse_data(self, raw_data)
    def detect_changes(self, new_data, existing_data)
    def update_database(self, changes)
    def verify_data_quality(self)
```

### 3. Texas Adapter (`deploy/adapters/texas_adapter.py`)
- Implements StateAdapter interface
- Texas-specific API calls
- Texas data format parsing
- Texas-specific validation

### 4. Change Log Table (Multi-State)
```sql
CREATE TABLE data_update_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_timestamp TEXT NOT NULL,
    state_code TEXT NOT NULL,  -- 'TX', 'CA', etc.
    data_source TEXT NOT NULL,  -- 'EVR', 'ELECTION_DAY', etc.
    election_id TEXT,
    election_date TEXT,
    records_before INTEGER,
    records_after INTEGER,
    records_added INTEGER,
    records_updated INTEGER,
    records_verified INTEGER,  -- County-verified count
    changes_detected INTEGER,  -- 0 or 1
    summary TEXT,
    details TEXT,  -- JSON with detailed changes
    error_message TEXT,
    duration_seconds REAL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_update_log_state ON data_update_log(state_code, created_at);
CREATE INDEX idx_update_log_election ON data_update_log(election_id, election_date);
```

### 3. Cron Job
Runs every 4 hours: `0 */4 * * *`

### 4. Admin Dashboard Integration
- New "Data Updates" section showing:
  - Last update time
  - Changes detected
  - Records added/updated
  - Full change log with details

## Files to Create
1. `deploy/auto_update_scraper.py` - Main scraper with change detection
2. `backend/data_updates.py` - API endpoints for admin dashboard
3. `backend/admin/data-updates.html` - Admin UI for viewing logs
4. `backend/admin/data-updates.js` - Frontend logic
5. `deploy/setup_cron.sh` - Cron job setup script

## Workflow
1. Cron triggers scraper every 4 hours
2. Scraper fetches latest data from Texas SOS
3. Compares with database (record counts, VUIDs, etc.)
4. If changes detected:
   - Updates database
   - Marks county data as verified
   - Regenerates district caches
   - Logs detailed changes
5. Admin can view all changes in dashboard

## Implementation Steps
1. Create data_update_log table
2. Build auto_update_scraper.py
3. Add API endpoints
4. Create admin UI
5. Setup cron job
6. Test end-to-end


### 5. Admin Dashboard Integration
- New "Data Updates" section showing:
  - Per-state update status
  - Last update time per state
  - Changes detected
  - Records added/updated/verified
  - Full change log with filtering by state/date
  - Error tracking and alerts

### 6. State Configuration File (`config/states.json`)
- Centralized state configuration
- Easy to add new states
- Per-state settings and API endpoints

## Directory Structure
```
deploy/
├── auto_update_orchestrator.py      # Main coordinator
├── adapters/
│   ├── base_adapter.py              # Abstract base class
│   ├── texas_adapter.py             # Texas implementation
│   └── [future_state]_adapter.py    # Future state adapters
├── config/
│   └── states.json                  # State configurations
└── utils/
    ├── change_detector.py           # Generic change detection
    ├── data_validator.py            # Data quality checks
    └── cache_regenerator.py         # Cache rebuild logic

backend/
├── data_updates.py                  # API endpoints
└── admin/
    ├── data-updates.html            # Admin UI
    └── data-updates.js              # Frontend logic
```

## Workflow
1. Cron triggers orchestrator every 4 hours (configurable per state)
2. Orchestrator loads enabled states from config
3. For each state:
   - Load state adapter
   - Fetch latest data from state API
   - Detect changes (new records, updates)
   - If changes detected:
     - Update database
     - Mark county data as verified
     - Regenerate district caches
     - Log detailed changes
4. Admin dashboard shows real-time status

## Adding a New State
1. Create new adapter: `deploy/adapters/newstate_adapter.py`
2. Implement StateAdapter interface
3. Add state config to `config/states.json`
4. Test adapter independently
5. Enable in production

## Implementation Priority
1. ✓ Design multi-state architecture
2. Create base adapter interface
3. Implement Texas adapter (refactor existing code)
4. Build orchestrator
5. Create data_update_log table
6. Add API endpoints
7. Build admin UI
8. Setup cron job
9. Test end-to-end
10. Document for future states

## Future State Examples
- California: Different API, different data format
- Florida: County-level APIs, aggregation needed
- Georgia: PDF parsing required
- etc.

Each state adapter handles its unique requirements while the orchestrator provides consistent logging, scheduling, and admin interface.
