---
inclusion: auto
---

# Database Schema Reference

## Database Type: SQLite3
- Path: `/opt/whovoted/data/whovoted.db`
- Connection: `sqlite3.connect('/opt/whovoted/data/whovoted.db')`
- Placeholders: `?` (NOT `%s`)

## Key Tables

### voters
- `vuid` (TEXT PRIMARY KEY)
- `precinct` (TEXT) - NOT `voting_precinct`
- `lat` (REAL) - NOT `latitude`
- `lng` (REAL) - NOT `longitude`
- `county` (TEXT)
- `congressional_district` (TEXT)
- `state_house_district` (TEXT)
- `state_senate_district` (TEXT)
- `commissioner_district` (TEXT)

### voter_elections
- `vuid` (TEXT)
- `election_date` (TEXT)
- `party_voted` (TEXT)
- `voting_method` (TEXT)

### district_counts_cache
- `district_type` (TEXT)
- `district_number` (TEXT)
- `county` (TEXT)
- `total_voters` (INTEGER)
- `voted_2024_general` (INTEGER)
- `voted_2024_primary` (INTEGER)

## ALWAYS Check Schema First
```python
# Check columns
conn.execute('PRAGMA table_info(table_name)').fetchall()

# Check tables
conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
```

## Common Mistakes to Avoid
- Assuming PostgreSQL syntax
- Using `%s` instead of `?`
- Column names: `voting_precinct`, `latitude`, `longitude`
- Table names: `early_voting`, `election_day`, `district_cache`
