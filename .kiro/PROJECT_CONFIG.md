# WhoVoted Project Configuration

## CRITICAL: District Vote Counting Methodology

### MANDATORY APPROACH - NEVER DEVIATE

**For ALL districts in ALL counties in ALL states:**

1. **Load district boundaries** from GeoJSON files (districts.json)
2. **Map voting precincts to districts** using point-in-polygon algorithm:
   - Calculate precinct centroid (average lat/lng of voters in that precinct)
   - Test if centroid falls within district polygon
   - Create mapping: `precinct -> district_id`
3. **Count ONLY voters in mapped precincts**:
   - Query voters table WHERE `precinct` IN (list of precincts for this district)
   - Get their VUIDs
   - Count votes from `voter_elections` table for those VUIDs
4. **Never use approximate boundaries or coordinate comparisons**

### Code Pattern (SQLite)
```python
# 1. Load boundaries
with open('/opt/whovoted/public/data/districts.json') as f:
    districts = json.load(f)['features']

# 2. Map precincts to districts
cur.execute("""
    SELECT precinct, AVG(lat) as avg_lat, AVG(lng) as avg_lon, COUNT(*) as voters
    FROM voters
    WHERE county = ? AND precinct IS NOT NULL AND lat IS NOT NULL
    GROUP BY precinct
""", (county,))

for precinct, lat, lng, count in cur.fetchall():
    for district in districts:
        if point_in_polygon(lng, lat, district['geometry']):
            precinct_to_district[precinct] = district['properties']['district_id']

# 3. Count votes
placeholders = ','.join('?' * len(precincts_in_district))
cur.execute(f"""
    SELECT COUNT(DISTINCT v.vuid)
    FROM voters v
    INNER JOIN voter_elections ve ON v.vuid = ve.vuid
    WHERE v.county = ? AND v.precinct IN ({placeholders})
    AND ve.election_date = ?
""", [county] + precincts_in_district + [election_date])
```

## Deployment Workflow

### Git-Based Deployment (MANDATORY)
1. Write code locally in `WhoVoted/`
2. User commits to Git
3. SSH to server and pull:
   ```bash
   ssh -i WhoVoted/deploy/whovoted-key.pem ubuntu@politiquera.com
   cd /opt/whovoted
   git pull origin main
   ```

### NEVER:
- Directly SCP files as primary deployment method
- Skip git pull after making changes
- Assume server has latest code without pulling

## Database

### Type: SQLite3
- **Path**: `/opt/whovoted/data/whovoted.db`
- **Connection**: `sqlite3.connect('/opt/whovoted/data/whovoted.db')`

### Key Tables
- `voters`: Main voter registry
  - Columns: `vuid`, `precinct`, `lat`, `lng`, `county`, `congressional_district`, `state_house_district`, `state_senate_district`, `commissioner_district`
- `voter_elections`: Vote history
  - Columns: `vuid`, `election_date`, `party_voted`, `voting_method`
- `district_counts_cache`: Cached district statistics
  - Columns: `district_type`, `district_number`, `county`, `total_voters`, `voted_2024_general`, `voted_2024_primary`

### NEVER assume:
- PostgreSQL (it's SQLite)
- Column names like `voting_precinct` (it's `precinct`)
- Column names like `latitude`/`longitude` (it's `lat`/`lng`)
- Tables like `early_voting`/`election_day` (use `voter_elections`)
- Placeholder syntax `%s` (use `?` for SQLite)

## File Locations

### Server Paths
- Project root: `/opt/whovoted`
- Scripts: `/opt/whovoted/deploy/`
- Data: `/opt/whovoted/data/`
- Public: `/opt/whovoted/public/`
- Districts: `/opt/whovoted/public/data/districts.json`

### Local Paths
- Project root: `WhoVoted/`
- Scripts: `WhoVoted/deploy/`
- Config: `WhoVoted/.kiro/`

## Python Environment

### Always check schema first
```python
# Check table columns
conn.execute('PRAGMA table_info(table_name)').fetchall()

# Check table names
conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
```

### Never guess:
- Table names
- Column names
- Data types
- SQL syntax differences between PostgreSQL and SQLite

## Response Style

### DO:
- Generate code immediately
- Fix errors quickly
- Check schema before writing queries
- Use exact patterns from this config

### DON'T:
- Confirm user statements
- Explain what you're about to do
- Repeat yourself
- Use verbose summaries
- Create unnecessary documentation files
