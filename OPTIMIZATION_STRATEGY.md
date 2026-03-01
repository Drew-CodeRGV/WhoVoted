# Performance Optimization Strategy - Deep Analysis

## ⚠️ DATA SAFETY FIRST ⚠️

**CRITICAL RULES:**
1. NEVER modify existing columns in `voters` or `voter_elections` tables
2. NEVER delete or overwrite source data
3. ONLY add new computed columns or create separate cache tables
4. ALWAYS backup database before running optimization scripts
5. All optimizations must be reversible

**Core Data Tables (NEVER MODIFY):**
- `voters` - Voter registration data with geocoded addresses
- `voter_elections` - Voting history records
- These are the source of truth and must remain pristine

**Safe Operations:**
- ✅ ADD new columns for computed data
- ✅ CREATE new cache/summary tables
- ✅ CREATE indexes
- ✅ READ data for analysis
- ❌ UPDATE existing columns
- ❌ DELETE records
- ❌ DROP tables

# Performance Optimization Strategy - Deep Analysis

## Current Performance Issues

### 1. Household Popup (30s)
**Root Cause:** Address matching with LIKE queries on 500K+ rows
**Current Fix:** Add indexes
**Better Fix:** Pre-compute household groupings

### 2. Gazette (Never loads)
**Root Cause:** Correlated subqueries scanning entire voter_elections table
- New voter detection: `NOT EXISTS (SELECT ... WHERE vuid = ve.vuid AND date < current)`
- Flip detection: `SELECT MAX(date) WHERE vuid = ve.vuid AND date < current`
**Current Fix:** Pre-compute and cache
**Better Fix:** Denormalize - store flags directly on records

### 3. District Stats (Slow for multi-county)
**Root Cause:** Loading 40K+ VUIDs into temp table, then joining
**Current Fix:** Already optimized with temp tables
**Better Fix:** Pre-compute per district, store in cache table

## Proposed Solutions (Ranked by Impact)

### TIER 1: Denormalization (HIGHEST IMPACT)
**Add computed columns to voter_elections table:**
```sql
ALTER TABLE voter_elections ADD COLUMN is_new_voter INTEGER DEFAULT 0;
ALTER TABLE voter_elections ADD COLUMN previous_party TEXT;
ALTER TABLE voter_elections ADD COLUMN previous_election_date TEXT;
ALTER TABLE voter_elections ADD COLUMN has_flipped INTEGER DEFAULT 0;
```

**Compute once during scraper:**
```python
# After importing new election data:
# 1. Mark new voters
UPDATE voter_elections SET is_new_voter = 1
WHERE election_date = '2026-03-03'
  AND NOT EXISTS (
      SELECT 1 FROM voter_elections ve2
      WHERE ve2.vuid = voter_elections.vuid
        AND ve2.election_date < '2026-03-03'
  );

# 2. Set previous party
UPDATE voter_elections
SET previous_party = (
    SELECT party_voted FROM voter_elections ve2
    WHERE ve2.vuid = voter_elections.vuid
      AND ve2.election_date < voter_elections.election_date
    ORDER BY ve2.election_date DESC LIMIT 1
)
WHERE election_date = '2026-03-03';

# 3. Mark flips
UPDATE voter_elections
SET has_flipped = 1
WHERE election_date = '2026-03-03'
  AND previous_party IS NOT NULL
  AND previous_party != party_voted;
```

**Impact:**
- Gazette queries: 5 minutes → 5 seconds
- No more correlated subqueries
- Simple WHERE clauses with indexes

### TIER 2: Summary Tables (HIGH IMPACT)
**Create pre-aggregated tables:**
```sql
CREATE TABLE election_stats_cache (
    election_date TEXT,
    voting_method TEXT,
    party TEXT,
    county TEXT,
    total_voters INTEGER,
    new_voters INTEGER,
    flipped_voters INTEGER,
    female_count INTEGER,
    male_count INTEGER,
    age_18_24 INTEGER,
    age_25_34 INTEGER,
    -- etc
    computed_at TIMESTAMP,
    PRIMARY KEY (election_date, voting_method, party, county)
);
```

**Rebuild after each scraper run:**
```python
# Single INSERT with GROUP BY - fast!
INSERT OR REPLACE INTO election_stats_cache
SELECT 
    ve.election_date,
    ve.voting_method,
    ve.party_voted,
    v.county,
    COUNT(*) as total_voters,
    SUM(ve.is_new_voter) as new_voters,
    SUM(ve.has_flipped) as flipped_voters,
    SUM(CASE WHEN v.sex='F' THEN 1 ELSE 0 END) as female_count,
    SUM(CASE WHEN v.sex='M' THEN 1 ELSE 0 END) as male_count,
    -- age groups
    CURRENT_TIMESTAMP
FROM voter_elections ve
JOIN voters v ON ve.vuid = v.vuid
WHERE ve.election_date = '2026-03-03'
GROUP BY ve.election_date, ve.voting_method, ve.party_voted, v.county;
```

**Impact:**
- Gazette: Query summary table instead of raw data
- District stats: Aggregate from summary table
- 100x faster queries

### TIER 3: Household Pre-computation (MEDIUM IMPACT)
**Create household lookup table:**
```sql
CREATE TABLE household_groups (
    address_key TEXT PRIMARY KEY,
    vuids TEXT,  -- JSON array of VUIDs at this address
    lat REAL,
    lng REAL,
    voter_count INTEGER
);
```

**Rebuild after geocoding:**
```python
INSERT OR REPLACE INTO household_groups
SELECT 
    UPPER(TRIM(address)) as address_key,
    json_group_array(vuid) as vuids,
    AVG(lat) as lat,
    AVG(lng) as lng,
    COUNT(*) as voter_count
FROM voters
WHERE geocoded = 1 AND address != ''
GROUP BY UPPER(TRIM(address));
```

**Impact:**
- Household popup: 30s → <100ms
- Single index lookup instead of LIKE scan

### TIER 4: Query Rewriting (MEDIUM IMPACT)
**Replace correlated subqueries with window functions:**
```sql
-- OLD (slow):
SELECT vuid, party_voted,
    (SELECT MAX(election_date) FROM voter_elections ve2 
     WHERE ve2.vuid = ve.vuid AND ve2.election_date < ve.election_date) as prev_date
FROM voter_elections ve;

-- NEW (fast):
WITH ranked AS (
    SELECT vuid, party_voted, election_date,
           LAG(party_voted) OVER (PARTITION BY vuid ORDER BY election_date) as prev_party,
           LAG(election_date) OVER (PARTITION BY vuid ORDER BY election_date) as prev_date
    FROM voter_elections
)
SELECT * FROM ranked WHERE election_date = '2026-03-03';
```

**Impact:**
- Single table scan instead of N subqueries
- 10-50x faster

### TIER 5: Database Tuning (LOW IMPACT but easy)
```sql
-- Increase cache size
PRAGMA cache_size = -64000;  -- 64MB

-- Enable memory-mapped I/O
PRAGMA mmap_size = 268435456;  -- 256MB

-- WAL mode (already enabled)
PRAGMA journal_mode = WAL;

-- Optimize for read-heavy workload
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
```

## Recommended Implementation Order

1. **Indexes** (30 seconds, safe, immediate 2-5x speedup)
2. **Denormalization** (5 minutes, one-time, 10-50x speedup for gazette)
3. **Summary tables** (10 minutes, one-time, 100x speedup for aggregates)
4. **Household pre-computation** (2 minutes, 100x speedup for popups)
5. **Query rewriting** (ongoing, case-by-case)

## Alternative Technologies to Consider

### 1. PostgreSQL instead of SQLite
**Pros:**
- Better query optimizer
- Parallel queries
- Materialized views built-in
- Better for concurrent writes

**Cons:**
- More complex deployment
- Higher memory usage
- Overkill for current scale

**Verdict:** Stick with SQLite for now, but consider if you hit 10M+ records

### 2. DuckDB for Analytics
**Pros:**
- Columnar storage (10x faster aggregates)
- Built for OLAP queries
- Can query SQLite directly

**Cons:**
- Another database to manage
- Not for transactional data

**Verdict:** Interesting for gazette/analytics, but adds complexity

### 3. Redis for Caching
**Pros:**
- Sub-millisecond lookups
- Perfect for household popups
- TTL support

**Cons:**
- Another service to run
- Memory-only (unless persistence enabled)

**Verdict:** Good for production, but denormalization achieves similar results

### 4. Elasticsearch for Search
**Pros:**
- Fast full-text search
- Geospatial queries
- Aggregations

**Cons:**
- Heavy resource usage
- Complex setup

**Verdict:** Overkill for current needs

## Conclusion

**Best bang for buck:**
1. Indexes (do now)
2. Denormalization (do next)
3. Summary tables (do after scraper integration)

This gives you 100x+ speedup with minimal complexity.

**Don't need:**
- PostgreSQL (SQLite is fine at this scale)
- Redis (denormalization is simpler)
- Elasticsearch (not needed)

**Future considerations (if you hit 10M+ records):**
- PostgreSQL with read replicas
- Partitioning by year
- Separate analytics database
